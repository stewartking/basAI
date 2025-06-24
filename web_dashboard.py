from flask import Flask, render_template_string
import threading, time, json, os
from data_simulator import simulate
from ai_diagnosis import analyze

app = Flask(__name__, static_folder="static")

# File-based storage for data history
DATA_FILE = "/tmp/building_data_history.json"
MAX_HISTORY = 20  # Reduced for performance

def load_data_store():
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError, IOError) as e:
        print(f"⚠️ Error loading data_store: {e}")
        return []

def save_data_store(data):
    try:
        data = data[:MAX_HISTORY]
        with open(DATA_FILE, "w") as f:
            json.dump(data, f)
    except (IOError, TypeError) as e:
        print(f"❌ Error saving data_store: {e}")

data_store = load_data_store()

def safe_json_dump(obj, indent=None, max_length=500):
    """Safely dump JSON, truncating if too large for logs."""
    try:
        json_str = json.dumps(obj, indent=indent)
        if len(json_str) > max_length and indent:
            summary = {
                "size": len(json_str),
                "keys": list(obj.keys()) if isinstance(obj, dict) else "non-dict",
                "sample": json_str[:100] + "..."
            }
            return f"Truncated (size: {len(json_str)} bytes): {json.dumps(summary, indent=2)}"
        return json_str
    except (TypeError, ValueError) as e:
        return f"JSON dump error: {str(e)}"

def worker():
    while True:
        print("🚀 Worker running...")
        try:
            data = simulate()
            print("📡 Simulated data:", safe_json_dump(data, indent=2))
            result = analyze(data)
            print("🧠 AI result:", safe_json_dump(result, indent=2))
            entry = {
                "status": json.dumps(result) if isinstance(result, dict) else str(result),
                "timestamp": data.get("timestamp") or time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "error": None,
                "raw_data": json.dumps(data)
            }
            data_store.insert(0, entry)
            save_data_store(data_store)
        except Exception as e:
            print("❌ Error in worker:", str(e))
            entry = {
                "status": json.dumps({"summary": "Error occurred", "abnormalities": [], "recommendations": []}),
                "error": str(e),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "raw_data": "{}"
            }
            data_store.insert(0, entry)
            save_data_store(data_store)
        time.sleep(60)

print("Starting worker thread...")
thread = threading.Thread(target=worker, daemon=True)
thread.start()

def format_summary(summary_data, raw_data=None):
    """Convert summary or raw data into a human-readable narrative."""
    try:
        lines = []
        if isinstance(summary_data, dict):
            if "chillerSystem" in summary_data:
                chiller = summary_data["chillerSystem"]
                comps = chiller.get("totalCompressorsRunning", "N/A")
                chilled = chiller.get("chilledWaterSupplyTemp", "N/A")
                lines.append(f"Chiller: {comps} compressors running, chilled water at {chilled}°F.")
            if "boilerSystem" in summary_data:
                boiler = summary_data["boilerSystem"]
                boilers = boiler.get("boilersOn", "N/A")
                hot = boiler.get("hotWaterSupplyTemp", "N/A")
                lines.append(f"Boiler: {boilers} boiler(s) on, hot water at {hot}°F.")
            if "airHandlers" in summary_data:
                ahu = summary_data["airHandlers"]
                ahus = ahu.get("totalAHUs", "N/A")
                supply = ahu.get("averageSupplyAirTemp", "N/A")
                lines.append(f"Air Handlers: {ahus} AHUs, average supply air at {supply}°F.")
            if lines:
                return " ".join(lines)
        
        # Fallback to raw_data
        if raw_data and isinstance(raw_data, dict) and "equipment" in raw_data:
            equipment = raw_data["equipment"]
            if "ChillerSystem" in equipment:
                chiller = equipment["ChillerSystem"]
                comps = sum(1 for k in chiller if k.startswith("Compressor") and chiller[k].get("status") == "Running")
                chilled = chiller.get("chilledWaterSupplyTemp", "N/A")
                lines.append(f"Chiller: {comps} compressors running, chilled water at {chilled}°F.")
            if "BoilerSystem" in equipment:
                boiler = equipment["BoilerSystem"]
                boilers = sum(1 for k in boiler if k.startswith("Boiler") and boiler[k].get("burnerStatus") == "On")
                hot = boiler.get("hotWaterSupplyTemp", "N/A")
                lines.append(f"Boiler: {boilers} boiler(s) on, hot water at {hot}°F.")
            if "AirHandlers" in equipment:
                ahu = equipment["AirHandlers"]
                ahus = len([k for k in ahu if k.startswith("AHU")])
                supply_temps = [ahu[k].get("supplyAirTemp", 0) for k in ahu if k.startswith("AHU")]
                supply = round(sum(supply_temps) / len(supply_temps), 1) if supply_temps else "N/A"
                lines.append(f"Air Handlers: {ahus} AHUs, average supply air at {supply}°F.")
            if lines:
                return " ".join(lines)
        
        return "No system data available."
    except Exception as e:
        print(f"⚠️ Error formatting summary: {e}")
        return f"Error formatting summary: {str(e)}"

def format_abnormalities(abnormalities, raw_data=None):
    """Convert abnormalities into a list of readable strings."""
    try:
        result = []
        if isinstance(abnormalities, list):
            for ab in abnormalities:
                if isinstance(ab, dict) and "component" in ab and "issue" in ab:
                    value = f" ({ab.get('value', '')}{', normal range: ' + ab['normalRange'] if 'normalRange' in ab else ''})"
                    result.append(f"{ab['component']}: {ab['issue']}{value}")
        
        # Fallback: Check raw_data
        if not result and raw_data and isinstance(raw_data, dict) and "equipment" in raw_data:
            equipment = raw_data["equipment"]
            if "ChillerSystem" in equipment:
                chiller = equipment["ChillerSystem"]
                for i in range(1, 4):
                    comp = chiller.get(f"Compressor0{i}")
                    if comp and comp.get("dischargePressure", 0) > 350:
                        result.append(f"Compressor0{i}: High discharge pressure ({comp['dischargePressure']} psig, normal range: 300-350)")
            if "BoilerSystem" in equipment:
                boiler = equipment["BoilerSystem"]
                for i in range(1, 3):
                    b = boiler.get(f"Boiler0{i}")
                    if b and b.get("burnerStatus") == "Off" and b.get("supplyTemp", 0) > 150:
                        result.append(f"Boiler0{i}: Burner off but high supply temp ({b['supplyTemp']}°F)")
            if "AirHandlers" in equipment:
                ahu = equipment["AirHandlers"]
                for i in range(1, 4):
                    unit = ahu.get(f"AHU0{i}")
                    if unit and unit.get("supplyAirTemp", 0) < 58:
                        result.append(f"AHU0{i}: Low supply air temperature ({unit['supplyAirTemp']}°F, normal range: 58-62)")
        
        return result
    except Exception as e:
        print(f"⚠️ Error formatting abnormalities: {e}")
        return []

def format_recommendations(recommendations, abnormalities):
    """Convert recommendations into a list of readable strings."""
    try:
        result = []
        if isinstance(recommendations, list):
            for rec in recommendations:
                if isinstance(rec, dict) and "action" in rec:
                    priority = f" (Priority: {rec.get('priority', 'N/A')})"
                    result.append(f"{rec['action']}{priority}")
        
        # Fallback: Generate recommendations
        if abnormalities and not result:
            result = []
            if any("Compressor" in ab for ab in abnormalities):
                result.extend([
                    "Check chiller condenser for fouling or scaling (Priority: High)",
                    "Inspect cooling tower fan operation (Priority: Medium)"
                ])
            if any("Boiler" in ab for ab in abnormalities):
                result.append("Investigate boiler sensor or control issues (Priority: Medium)")
            if any("AHU" in ab for ab in abnormalities):
                result.append("Check AHU cooling coils and temperature sensors (Priority: Medium)")
        
        return result
    except Exception as e:
        print(f"⚠️ Error formatting recommendations: {e}")
        return []

# HTML template with polished design
TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Building AI Dashboard</title>
    <meta charset="UTF-8">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { font-family: 'Inter', sans-serif; }
        .data-card { transition: all 0.3s ease; border-radius: 1rem; }
        .data-card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.15); }
        .error { color: #ef4444; }
        th, td { padding: 1rem; }
        .summary-text { line-height: 1.6; font-size: 0.95rem; }
        .timestamp { font-size: 0.85rem; color: #6b7280; }
        .alert { background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 0.75rem; margin-bottom: 1rem; }
    </style>
</head>
<body class="bg-gray-50">
    <div class="max-w-5xl mx-auto p-6">
        <div class="mb-6 flex items-center">
            <img src="{{ url_for('static', filename='logo.png') }}" alt="Company Logo" class="h-12 w-auto" onerror="this.src='https://via.placeholder.com/150x50?text=Your+Logo'">
            <h1 class="text-2xl font-bold text-gray-900 ml-4">Building AI Dashboard</h1>
        </div>
        <div id="data-container">
            {% for entry in data_store %}
            <div class="data-card bg-white shadow-lg mb-6">
                <div class="p-5">
                    <p class="timestamp mb-2">Timestamp: {{ entry.timestamp }}</p>
                    {% if entry.error %}
                    <p class="error font-semibold mb-3">Error: {{ entry.error }}</p>
                    {% endif %}
                    {% if entry.status.abnormalities|length > 0 %}
                    <div class="alert">
                        <p class="text-sm font-semibold text-red-600">Attention: {{ entry.status.abnormalities|length }} issue(s) detected</p>
                    </div>
                    {% endif %}
                    <h2 class="text-lg font-semibold text-gray-800 mb-3">Building Status</h2>
                    <table class="w-full border-collapse">
                        <thead>
                            <tr class="bg-gray-100">
                                <th class="border border-gray-200 text-left text-sm font-semibold text-gray-700">Section</th>
                                <th class="border border-gray-200 text-left text-sm font-semibold text-gray-700">Details</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td class="border border-gray-200 text-sm font-medium text-gray-600">Summary</td>
                                <td class="border border-gray-200 text-sm text-gray-800 summary-text">{{ entry.status.summary }}</td>
                            </tr>
                            <tr>
                                <td class="border border-gray-200 text-sm font-medium text-gray-600">Abnormalities</td>
                                <td class="border border-gray-200 text-sm {% if entry.status.abnormalities|length > 0 %}text-red-600{% else %}text-green-600{% endif %}">
                                    {% if entry.status.abnormalities %}
                                        <ul class="list-disc pl-4">
                                            {% for item in entry.status.abnormalities %}
                                                <li>{{ item }}</li>
                                            {% endfor %}
                                        </ul>
                                    {% else %}
                                        None
                                    {% endif %}
                                </td>
                            </tr>
                            <tr>
                                <td class="border border-gray-200 text-sm font-medium text-gray-600">Recommendations</td>
                                <td class="border border-gray-200 text-sm text-gray-800">
                                    {% if entry.status.recommendations %}
                                        <ul class="list-disc pl-4">
                                            {% for item in entry.status.recommendations %}
                                                <li>{{ item }}</li>
                                            {% endfor %}
                                        </ul>
                                    {% else %}
                                        None
                                    {% endif %}
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
            <hr class="border-gray-200 my-4">
            {% endfor %}
        </div>
    </div>
    <script>
        async function fetchNewData() {
            try {
                const response = await fetch('/latest');
                const newEntry = await response.json();
                if (newEntry && newEntry.timestamp) {
                    const container = document.getElementById('data-container');
                    const div = document.createElement('div');
                    div.className = 'data-card bg-white shadow-lg mb-6';
                    div.innerHTML = `
                        <div class="p-5">
                            <p class="timestamp mb-2">Timestamp: ${newEntry.timestamp}</p>
                            ${newEntry.error ? `<p class="error font-semibold mb-3">Error: ${newEntry.error}</p>` : ''}
                            ${newEntry.status.abnormalities.length > 0 ? `
                                <div class="alert">
                                    <p class="text-sm font-semibold text-red-600">Attention: ${newEntry.status.abnormalities.length} issue(s) detected</p>
                                </div>
                            ` : ''}
                            <h2 class="text-lg font-semibold text-gray-800 mb-3">Building Status</h2>
                            <table class="w-full border-collapse">
                                <thead>
                                    <tr class="bg-gray-100">
                                        <th class="border border-gray-200 text-left text-sm font-semibold text-gray-700">Section</th>
                                        <th class="border border-gray-200 text-left text-sm font-semibold text-gray-700">Details</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td class="border border-gray-200 text-sm font-medium text-gray-600">Summary</td>
                                        <td class="border border-gray-200 text-sm text-gray-800 summary-text">${newEntry.status.summary || 'No summary available'}</td>
                                    </tr>
                                    <tr>
                                        <td class="border border-gray-200 text-sm font-medium text-gray-600">Abnormalities</td>
                                        <td class="border border-gray-200 text-sm ${newEntry.status.abnormalities.length > 0 ? 'text-red-600' : 'text-green-600'}">
                                            ${newEntry.status.abnormalities.length > 0 ? `
                                                <ul class="list-disc pl-4">
                                                    ${newEntry.status.abnormalities.map(item => `<li>${item}</li>`).join('')}
                                                </ul>
                                            ` : 'None'}
                                        </td>
                                    </tr>
                                    <tr>
                                        <td class="border border-gray-200 text-sm font-medium text-gray-600">Recommendations</td>
                                        <td class="border border-gray-200 text-sm text-gray-800">
                                            ${newEntry.status.recommendations.length > 0 ? `
                                                <ul class="list-disc pl-4">
                                                    ${newEntry.status.recommendations.map(item => `<li>${item}</li>`).join('')}
                                                </ul>
                                            ` : 'None'}
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    `;
                    container.insertBefore(div, container.firstChild);
                    const hr = document.createElement('hr');
                    hr.className = 'border-gray-200 my-4';
                    container.insertBefore(hr, div.nextSibling);
                    const cards = container.querySelectorAll('.data-card');
                    if (cards.length > {{ MAX_HISTORY }}) {
                        container.removeChild(container.lastChild);
                        container.removeChild(container.lastChild);
                    }
                }
            } catch (e) {
                console.error('Failed to fetch new data:', e);
            }
        }
        setInterval(fetchNewData, 60000);
        fetchNewData();
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    global data_store
    data_store = load_data_store()
    print("📥 Dashboard hit — latest:", safe_json_dump(data_store[:2], indent=2))
    processed_data = []
    for entry in data_store:
        try:
            status = json.loads(entry["status"]) if entry["status"] else {}
            raw_data = json.loads(entry.get("raw_data", "{}"))
            summary = status.get("summary", "No summary available")
            abnormalities = status.get("abnormalities", [])
            recommendations = status.get("recommendations", [])
            
            # Parse JSON code block
            if isinstance(summary, str) and summary.startswith("```json\n") and summary.endswith("\n```"):
                try:
                    nested_data = json.loads(summary[8:-4])
                    if isinstance(nested_data, dict):
                        summary = nested_data.get("summary", summary)
                        abnormalities = nested_data.get("abnormalities", abnormalities)
                        recommendations = nested_data.get("recommendations", recommendations)
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"⚠️ Error parsing JSON code block: {e}")
            
            # Format data
            if isinstance(summary, dict):
                summary = format_summary(summary, raw_data)
            elif not summary.strip() or summary == "No summary available":
                summary = format_summary({}, raw_data)
            
            abnormalities = format_abnormalities(abnormalities, raw_data)
            recommendations = format_recommendations(recommendations, abnormalities)
            
            status = {
                "summary": str(summary),
                "abnormalities": abnormalities,
                "recommendations": recommendations
            }
            processed_data.append({"status": status, "timestamp": entry["timestamp"], "error": entry.get("error")})
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            print(f"⚠️ Error parsing status for timestamp {entry['timestamp']}: {e}")
            processed_data.append({
                "status": {"summary": "Error parsing data", "abnormalities": [], "recommendations": []},
                "timestamp": entry["timestamp"],
                "error": f"Parsing error: {str(e)}"
            })
    return render_template_string(TEMPLATE, data_store=processed_data, MAX_HISTORY=MAX_HISTORY)

@app.route("/latest")
def latest():
    global data_store
    data_store = load_data_store()
    if not data_store:
        return json.dumps({
            "status": {"summary": "No data available", "abnormalities": [], "recommendations": []},
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "error": "No data available"
        })
    entry = data_store[0]
    try:
        status = json.loads(entry["status"]) if entry["status"] else {}
        raw_data = json.loads(entry.get("raw_data", "{}"))
        summary = status.get("summary", "No summary available")
        abnormalities = status.get("abnormalities", [])
        recommendations = status.get("recommendations", [])
        
        # Parse JSON code block
        if isinstance(summary, str) and summary.startswith("```json\n") and summary.endswith("\n```"):
            try:
                nested_data = json.loads(summary[8:-4])
                if isinstance(nested_data, dict):
                    summary = nested_data.get("summary", summary)
                    abnormalities = nested_data.get("abnormalities", abnormalities)
                    recommendations = nested_data.get("recommendations", recommendations)
            except (json.JSONDecodeError, ValueError) as e:
                print(f"⚠️ Error parsing JSON code block: {e}")
        
        # Format data
        if isinstance(summary, dict):
            summary = format_summary(summary, raw_data)
        elif not summary.strip() or summary == "No summary available":
            summary = format_summary({}, raw_data)
        
        abnormalities = format_abnormalities(abnormalities, raw_data)
        recommendations = format_recommendations(recommendations, abnormalities)
        
        status = {
            "summary": str(summary),
            "abnormalities": abnormalities,
            "recommendations": recommendations
        }
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        print(f"⚠️ Error parsing latest status: {e}")
        status = {"summary": "Error parsing data", "abnormalities": [], "recommendations": []}
        entry["error"] = f"Parsing error: {str(e)}"
    return json.dumps({"status": status, "timestamp": entry["timestamp"], "error": entry.get("error")})

@app.route("/debug")
def debug():
    try:
        with open(DATA_FILE, "r") as f:
            return f"<pre>{json.dumps(json.load(f), indent=2)}</pre>"
    except Exception as e:
        return f"Error reading data_store: {str(e)}"

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
