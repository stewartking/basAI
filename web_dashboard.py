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

def worker():
    while True:
        print("🚀 Worker running...")
        try:
            data = simulate()
            print("📡 Simulated data:", json.dumps(data, indent=2))
            result = analyze(data)
            print("🧠 AI result:", json.dumps(result, indent=2))
            entry = {
                "status": json.dumps(result) if isinstance(result, dict) else str(result),
                "timestamp": data.get("timestamp") or time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "error": None
            }
            data_store.insert(0, entry)
            save_data_store(data_store)
        except Exception as e:
            print("❌ Error in worker:", e)
            entry = {
                "status": json.dumps({"summary": "Error occurred", "abnormalities": [], "recommendations": []}),
                "error": str(e),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
            }
            data_store.insert(0, entry)
            save_data_store(data_store)
        time.sleep(60)

print("Starting worker thread...")
thread = threading.Thread(target=worker, daemon=True)
thread.start()

def format_summary(summary_data):
    """Convert JSON summary into a human-readable narrative."""
    if not isinstance(summary_data, dict):
        return "No summary data available."
    
    try:
        lines = []
        # ChillerSystem
        if "ChillerSystem" in summary_data:
            chiller = summary_data["ChillerSystem"]
            comps = chiller.get("totalCompressorsRunning", 0)
            chilled_supply = chiller.get("chilledWaterSupplyTemp", "N/A")
            cooling_fan = chiller.get("coolingTowerFanSpeed", "N/A")
            lines.append(f"Chiller System: {comps} compressors running, chilled water supply at {chilled_supply}°F, cooling tower fan at {cooling_fan}%.")
        
        # BoilerSystem
        if "BoilerSystem" in summary_data:
            boiler = summary_data["BoilerSystem"]
            boilers_on = boiler.get("boilersOn", 0)
            hot_supply = boiler.get("hotWaterSupplyTemp", "N/A")
            pump = boiler.get("pumpStatus", "Unknown")
            lines.append(f"Boiler System: {boilers_on} boiler(s) on, hot water supply at {hot_supply}°F, pump {pump.lower()}.")
        
        # AirHandlers
        if "AirHandlers" in summary_data:
            ahu = summary_data["AirHandlers"]
            total_ahus = ahu.get("totalAHUs", 0)
            supply_air = ahu.get("averageSupplyAirTemp", "N/A")
            lines.append(f"Air Handlers: {total_ahus} AHUs operating, average supply air at {supply_air}°F.")
        
        # Radiators
        if "Radiators" in summary_data:
            rad = summary_data["Radiators"]
            total_rads = rad.get("totalRadiators", 0)
            space_temp = rad.get("averageSpaceTemp", "N/A")
            lines.append(f"Radiators: {total_rads} radiators, average space temperature at {space_temp}°F.")
        
        return " ".join(lines) if lines else "No system data available."
    except Exception as e:
        print(f"⚠️ Error formatting summary: {e}")
        return "Error formatting summary data."

# HTML template with enhanced polish
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
        .data-card { transition: all 0.3s ease; border-radius: 0.5rem; }
        .data-card:hover { transform: translateY(-2px); box-shadow: 0 10px 15px rgba(0, 0, 0, 0.1); }
        .error { color: #ef4444; }
        th, td { padding: 0.75rem 1rem; }
        .summary-text { line-height: 1.6; }
    </style>
</head>
<body class="bg-gray-50">
    <div class="max-w-5xl mx-auto p-8">
        <div class="mb-8 flex items-center">
            <img src="{{ url_for('static', filename='logo.png') }}" alt="Company Logo" class="h-14 w-auto" onerror="this.src='https://via.placeholder.com/150x50?text=Your+Logo'">
            <h1 class="text-4xl font-bold text-gray-800 ml-4">Building AI Dashboard</h1>
        </div>
        <div id="data-container">
            {% for entry in data_store %}
            <div class="data-card bg-white shadow-lg mb-8">
                <div class="p-6">
                    <p class="text-sm text-gray-500 mb-2">Timestamp: {{ entry.timestamp }}</p>
                    {% if entry.error %}
                    <p class="error font-semibold mb-4">Error: {{ entry.error }}</p>
                    {% endif %}
                    <h2 class="text-xl font-semibold text-gray-700 mb-4">Building Status</h2>
                    <table class="w-full border-collapse">
                        <thead>
                            <tr class="bg-gray-100">
                                <th class="border border-gray-200 text-left text-sm font-semibold text-gray-600">Section</th>
                                <th class="border border-gray-200 text-left text-sm font-semibold text-gray-600">Details</th>
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
                                        {% if entry.status.abnormalities is mapping %}
                                            {% for equipment, details in entry.status.abnormalities.items() %}
                                                <strong>{{ equipment }}:</strong><br>
                                                {% if details is string %}
                                                    {{ details }}<br>
                                                {% elif details is mapping %}
                                                    {% for key, value in details.items() %}
                                                        {{ key }}: {{ value }}<br>
                                                    {% endfor %}
                                                {% else %}
                                                    <ul class="list-disc pl-4">
                                                    {% for item in details %}
                                                        <li>{{ item }}</li>
                                                    {% endfor %}
                                                    </ul>
                                                {% endif %}
                                            {% endfor %}
                                        {% else %}
                                            <ul class="list-disc pl-4">
                                            {% for item in entry.status.abnormalities %}
                                                <li>{{ item }}</li>
                                            {% endfor %}
                                            </ul>
                                        {% endif %}
                                    {% else %}
                                        None
                                    {% endif %}
                                </td>
                            </tr>
                            <tr>
                                <td class="border border-gray-200 text-sm font-medium text-gray-600">Recommendations</td>
                                <td class="border border-gray-200 text-sm text-gray-800">
                                    {% if entry.status.recommendations %}
                                        {% if entry.status.recommendations is mapping %}
                                            {% for equipment, details in entry.status.recommendations.items() %}
                                                <strong>{{ equipment }}:</strong><br>
                                                {% if details is string %}
                                                    {{ details }}<br>
                                                {% elif details is mapping %}
                                                    {% for key, value in details.items() %}
                                                        {{ key }}: {{ value }}<br>
                                                    {% endfor %}
                                                {% else %}
                                                    <ul class="list-disc pl-4">
                                                    {% for rec in details %}
                                                        <li>{{ rec }}</li>
                                                    {% endfor %}
                                                    </ul>
                                                {% endif %}
                                            {% endfor %}
                                        {% else %}
                                            <ul class="list-disc pl-4">
                                            {% for item in entry.status.recommendations %}
                                                <li>{{ item }}</li>
                                            {% endfor %}
                                            </ul>
                                        {% endif %}
                                    {% else %}
                                        None
                                    {% endif %}
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
            <hr class="border-gray-300 my-6">
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
                    div.className = 'data-card bg-white shadow-lg mb-8';
                    div.innerHTML = `
                        <div class="p-6">
                            <p class="text-sm text-gray-500 mb-2">Timestamp: ${newEntry.timestamp}</p>
                            ${newEntry.error ? `<p class="error font-semibold mb-4">Error: ${newEntry.error}</p>` : ''}
                            <h2 class="text-xl font-semibold text-gray-700 mb-4">Building Status</h2>
                            <table class="w-full border-collapse">
                                <thead>
                                    <tr class="bg-gray-100">
                                        <th class="border border-gray-200 text-left text-sm font-semibold text-gray-600">Section</th>
                                        <th class="border border-gray-200 text-left text-sm font-semibold text-gray-600">Details</th>
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
                                            ${newEntry.status.abnormalities.length > 0 ? (
                                                Array.isArray(newEntry.status.abnormalities) ?
                                                    `<ul class="list-disc pl-4">${newEntry.status.abnormalities.map(item => `<li>${item}</li>`).join('')}</ul>` :
                                                    Object.entries(newEntry.status.abnormalities).map(([equip, details]) => `
                                                        <strong>${equip}:</strong><br>
                                                        ${typeof details === 'string' ? details :
                                                          Array.isArray(details) ? `<ul class="list-disc pl-4">${details.map(item => `<li>${item}</li>`).join('')}</ul>` :
                                                          Object.entries(details).map(([k, v]) => `${k}: ${v}<br>`).join('')}
                                                    `).join('')
                                            ) : 'None'}
                                        </td>
                                    </tr>
                                    <tr>
                                        <td class="border border-gray-200 text-sm font-medium text-gray-600">Recommendations</td>
                                        <td class="border border-gray-200 text-sm text-gray-800">
                                            ${newEntry.status.recommendations.length > 0 ? (
                                                Array.isArray(newEntry.status.recommendations) ?
                                                    `<ul class="list-disc pl-4">${newEntry.status.recommendations.map(item => `<li>${item}</li>`).join('')}</ul>` :
                                                    Object.entries(newEntry.status.recommendations).map(([equip, details]) => `
                                                        <strong>${equip}:</strong><br>
                                                        ${typeof details === 'string' ? details :
                                                          Array.isArray(details) ? `<ul class="list-disc pl-4">${details.map(rec => `<li>${rec}</li>`).join('')}</ul>` :
                                                          Object.entries(details).map(([k, v]) => `${k}: ${v}<br>`).join('')}
                                                    `).join('')
                                            ) : 'None'}
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    `;
                    container.insertBefore(div, container.firstChild);
                    const hr = document.createElement('hr');
                    hr.className = 'border-gray-300 my-6';
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
    print("📥 Dashboard hit — latest:", json.dumps(data_store[:2], indent=2))
    processed_data = []
    for entry in data_store:
        try:
            status = json.loads(entry["status"]) if entry["status"] else {}
            # Handle LLM output
            summary = status.get("summary", "No summary available")
            if isinstance(summary, dict):
                summary = format_summary(summary)
            elif isinstance(summary, str) and summary.startswith("```json\n") and summary.endswith("\n```"):
                try:
                    summary = json.loads(summary[8:-4])
                    summary = format_summary(summary)
                except (json.JSONDecodeError, ValueError):
                    pass  # Use raw summary string
            # Ensure status has required fields
            status = {
                "summary": str(summary),
                "abnormalities": status.get("abnormalities", []),
                "recommendations": status.get("recommendations", [])
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
        summary = status.get("summary", "No summary available")
        if isinstance(summary, dict):
            summary = format_summary(summary)
        elif isinstance(summary, str) and summary.startswith("```json\n") and summary.endswith("\n```"):
            try:
                summary = json.loads(summary[8:-4])
                summary = format_summary(summary)
            except (json.JSONDecodeError, ValueError):
                pass  # Use raw summary string
        status = {
            "summary": str(summary),
            "abnormalities": status.get("abnormalities", []),
            "recommendations": status.get("recommendations", [])
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
