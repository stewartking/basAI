from flask import Flask, render_template_string
import threading, time, json, os
from data_simulator import simulate
from ai_diagnosis import analyze

app = Flask(__name__, static_folder="static")

# File-based storage for data history
DATA_FILE = "/tmp/building_data_history.json"
MAX_HISTORY = 50

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

def safe_json_dump(obj, indent=None, max_length=1000):
    """Safely dump JSON, truncating if too large for logs."""
    try:
        json_str = json.dumps(obj, indent=indent)
        if len(json_str) > max_length and indent:
            summary = {
                "size": len(json_str),
                "keys": list(obj.keys()) if isinstance(obj, dict) else "non-dict",
                "sample": json_str[:200] + "..."
            }
            return f"Truncated (full size: {len(json_str)} bytes): {json.dumps(summary, indent=2)}"
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
        # Try LLM summary first
        if isinstance(summary_data, dict):
            if "chillerSystem" in summary_data:
                chiller = summary_data["chillerSystem"]
                comps = chiller.get("totalCompressorsRunning", "N/A")
                chilled = chiller.get("chilledWaterSupplyTemp", "N/A")
                fan = chiller.get("coolingTowerFanSpeed", "N/A")
                lines.append(f"Chiller: {comps} compressors, chilled water at {chilled}°F, cooling tower fan at {fan}%.")
            if "boilerSystem" in summary_data:
                boiler = summary_data["boilerSystem"]
                boilers = boiler.get("boilersOn", "N/A")
                hot = boiler.get("hotWaterSupplyTemp", "N/A")
                pump = boiler.get("pumpStatus", "Unknown")
                lines.append(f"Boiler: {boilers} boiler(s) on, hot water at {hot}°F, pump {pump.lower()}.")
            if "airHandlers" in summary_data:
                ahu = summary_data["airHandlers"]
                ahus = ahu.get("totalAHUs", "N/A")
                supply = ahu.get("averageSupplyAirTemp", "N/A")
                lines.append(f"Air Handlers: {ahus} AHUs, supply air at {supply}°F.")
            if "radiators" in summary_data:
                rad = summary_data["radiators"]
                rads = rad.get("totalRadiators", "N/A")
                temp = rad.get("averageSpaceTemp", "N/A")
                lines.append(f"Radiators: {rads} radiators, space temp at {temp}°F.")
            if lines:
                return " ".join(lines)
        
        # Fallback to raw_data
        if raw_data and isinstance(raw_data, dict) and "equipment" in raw_data:
            equipment = raw_data["equipment"]
            if "ChillerSystem" in equipment:
                chiller = equipment["ChillerSystem"]
                comps = sum(1 for k in chiller if k.startswith("Compressor") and chiller[k].get("status") == "Running")
                chilled = chiller.get("chilledWaterSupplyTemp", "N/A")
                fan = chiller.get("coolingTowerFanSpeed", "N/A")
                lines.append(f"Chiller: {comps} compressors, chilled water at {chilled}°F, cooling tower fan at {fan}%.")
            if "BoilerSystem" in equipment:
                boiler = equipment["BoilerSystem"]
                boilers = sum(1 for k in boiler if k.startswith("Boiler") and boiler[k].get("burnerStatus") == "On")
                hot = boiler.get("hotWaterSupplyTemp", "N/A")
                pump = boiler.get("pumpStatus", "Unknown")
                lines.append(f"Boiler: {boilers} boiler(s) on, hot water at {hot}°F, pump {pump.lower()}.")
            if "AirHandlers" in equipment:
                ahu = equipment["AirHandlers"]
                ahus = len([k for k in ahu if k.startswith("AHU")])
                supply_temps = [ahu[k].get("supplyAirTemp", 0) for k in ahu if k.startswith("AHU")]
                supply = round(sum(supply_temps) / len(supply_temps), 1) if supply_temps else "N/A"
                lines.append(f"Air Handlers: {ahus} AHUs, supply air at {supply}°F.")
            if "Radiators" in equipment:
                rad = equipment["Radiators"]
                rads = len([k for k in rad if k.startswith("Rad")])
                temps = [rad[k].get("spaceTemp", 0) for k in rad if k.startswith("Rad")]
                temp = round(sum(temps) / len(temps), 1) if temps else "N/A"
                lines.append(f"Radiators: {rads} radiators, space temp at {temp}°F.")
            if lines:
                return " ".join(lines)
        
        return "No system data available."
    except Exception as e:
        print(f"⚠️ Error formatting summary: {e}")
        return f"Error formatting summary: {str(e)}"

def format_abnormalities(abnormalities):
    """Convert abnormalities into a list of readable strings."""
    if not abnormalities:
        return []
    try:
        if isinstance(abnormalities, list):
            return [
                f"{ab['component']}: {ab['issue']} ({ab.get('value', '')}{', normal range: ' + ab['normalRange'] if 'normalRange' in ab else ''})"
                for ab in abnormalities if isinstance(ab, dict) and "component" in ab and "issue" in ab
            ]
        return []
    except Exception as e:
        print(f"⚠️ Error formatting abnormalities: {e}")
        return []

def format_recommendations(recommendations):
    """Convert recommendations into a list of readable strings."""
    if not recommendations:
        return []
    try:
        if isinstance(recommendations, list):
            return [
                f"{rec['action']} (Priority: {rec.get('priority', 'N/A')})"
                for rec in recommendations if isinstance(rec, dict) and "action" in rec
            ]
        return []
    except Exception as e:
        print(f"⚠️ Error formatting recommendations: {e}")
        return []

# HTML template with fixed loop and polished design
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
        .data-card { transition: all 0.3s ease; border-radius: 0.75rem; }
        .data-card:hover { transform: translateY(-4px); box-shadow: 0 6px 20px rgba(0,0,0,0.1); }
        .error { color: #ef4444; }
        th, td { padding: 1.25rem; }
        .summary-text { line-height: 1.7; font-size: 1rem; }
        .timestamp { font-size: 0.875rem; color: #6b7280; }
    </style>
</head>
<body class="bg-gray-100">
    <div class="max-w-6xl mx-auto p-8">
        <div class="mb-8 flex items-center">
            <img src="{{ url_for('static', filename='logo.png') }}" alt="Company Logo" class="h-16 w-auto" onerror="this.src='https://via.placeholder.com/150x50?text=Your+Logo'">
            <h1 class="text-3xl font-bold text-gray-900 ml-4">Building AI Dashboard</h1>
        </div>
        <div id="data-container">
            {% for entry in data_store %}
            <div class="data-card bg-white shadow-md mb-8">
                <div class="p-6">
                    <p class="timestamp mb-2">Timestamp: {{ entry.timestamp }}</p>
                    {% if entry.error %}
                    <p class="error font-semibold mb-4">Error: {{ entry.error }}</p>
                    {% endif %}
                    <h2 class="text-xl font-semibold text-gray-800 mb-4">Building Status</h2>
                    <table class="w-full border-collapse">
                        <thead>
                            <tr class="bg-gray-50">
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
            <hr class="border-gray-200 my-6">
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
                    div.className = 'data-card bg-white shadow-md mb-8';
                    div.innerHTML = `
                        <div class="p-6">
                            <p class="timestamp mb-2">Timestamp: ${newEntry.timestamp}</p>
                            ${newEntry.error ? `<p class="error font-semibold mb-4">Error: ${newEntry.error}</p>` : ''}
                            <h2 class="text-xl font-semibold text-gray-800 mb-4">Building Status</h2>
                            <table class="w-full border-collapse">
                                <thead>
                                    <tr class="bg-gray-50">
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
                    hr.className = 'border-gray-200 my-6';
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
            
            # Parse JSON code block in summary
            if isinstance(summary, str) and summary.startswith("```json\n") and summary.endswith("\n```"):
                try:
                    nested_data = json.loads(summary[8:-4])
                    if isinstance(nested_data, dict):
                        # Extract nested fields
                        summary = nested_data.get("summary", summary)
                        abnormalities = nested_data.get("abnormalities", abnormalities)
                        recommendations = nested_data.get("recommendations", recommendations)
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"⚠️ Error parsing JSON code block: {e}")
            
            # Format summary
            if isinstance(summary, dict):
                summary = format_summary(summary, raw_data)
            elif not summary.strip() or summary == "No summary available":
                summary = format_summary({}, raw_data)
            
            # Format abnormalities and recommendations
            abnormalities = format_abnormalities(abnormalities)
            recommendations = format_recommendations(recommendations)
            
            # Fallback abnormalities
            if not abnormalities and raw_data.get("equipment", {}).get("ChillerSystem"):
                chiller = raw_data["equipment"]["ChillerSystem"]
                for i in range(1, 7):  # Check all compressors
                    comp = chiller.get(f"Compressor0{i}")
                    if comp and comp.get("dischargePressure", 0) > 350:  # Stricter threshold to align with LLM
                        abnormalities.append(f"Compressor0{i}: High discharge pressure ({comp['dischargePressure']} psig)")
            
            # Fallback recommendations
            if abnormalities and not recommendations:
                recommendations = [
                    "Check condenser water flow rate.",
                    "Inspect cooling tower fan speed.",
                    "Verify condenser for fouling or scaling."
                ]
            
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
        
        # Format summary
        if isinstance(summary, dict):
            summary = format_summary(summary, raw_data)
        elif not summary.strip() or summary == "No summary available":
            summary = format_summary({}, raw_data)
        
        # Format abnormalities and recommendations
        abnormalities = format_abnormalities(abnormalities)
        recommendations = format_recommendations(recommendations)
        
        # Fallback abnormalities
        if not abnormalities and raw_data.get("equipment", {}).get("ChillerSystem"):
            chiller = raw_data["equipment"]["ChillerSystem"]
            for i in range(1, 7):
                comp = chiller.get(f"Compressor0{i}")
                if comp and comp.get("dischargePressure", 0) > 350:
                    abnormalities.append(f"Compressor0{i}: High discharge pressure ({comp['dischargePressure']} psig)")
        
        # Fallback recommendations
        if abnormalities and not recommendations:
            recommendations = [
                "Check condenser water flow rate.",
                "Inspect cooling tower fan speed.",
                "Verify condenser for fouling or scaling."
            ]
        
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
