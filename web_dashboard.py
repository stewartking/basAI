from flask import Flask, render_template_string
import threading, time, json, os
from data_simulator import simulate
from ai_diagnosis import analyze

app = Flask(__name__, static_folder="static")

# File-based storage for data history
DATA_FILE = "/tmp/building_data_history.json"
MAX_HISTORY = 50

def load_data_store():
    """Load data history from file or initialize if not exists."""
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError, IOError) as e:
        print(f"⚠️ Error loading data_store: {e}")
        return []

def save_data_store(data):
    """Save data history to file, keeping up to MAX_HISTORY entries."""
    try:
        data = data[:MAX_HISTORY]
        with open(DATA_FILE, "w") as f:
            json.dump(data, f)
    except (IOError, TypeError) as e:
        print(f"❌ Error saving data_store: {e}")

data_store = load_data_store()

def worker():
    """Background worker to simulate and analyze BAS data."""
    while True:
        print("🚀 Worker running...")
        try:
            data = simulate()
            print("📡 Simulated data:", data)
            result = analyze(data)
            print("🧠 AI result:", result)
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
                "status": json.dumps({"summary": "Error occurred", "abnormalities": {}, "recommendations": {}}),
                "error": str(e),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
            }
            data_store.insert(0, entry)
            save_data_store(data_store)
        time.sleep(60)

print("Starting worker thread...")
thread = threading.Thread(target=worker, daemon=True)
thread.start()

# HTML template with Tailwind CSS and dynamic updates
TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Building AI Dashboard</title>
    <meta charset="UTF-8">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { font-family: 'Inter', sans-serif; }
        .data-card { transition: all 0.3s ease; }
        .data-card:hover { transform: translateY(-2px); }
        .error { color: #ef4444; }
    </style>
</head>
<body class="bg-gray-100">
    <div class="max-w-4xl mx-auto p-6">
        <div class="mb-6">
            <img src="{{ url_for('static', filename='logo.png') }}" alt="Company Logo" class="h-12 w-auto" onerror="this.src='https://via.placeholder.com/150x50?text=Your+Logo'">
        </div>
        <h1 class="text-3xl font-semibold text-gray-800 mb-4">Building AI Dashboard</h1>
        <div id="data-container">
            {% for entry in data_store %}
            <div class="data-card bg-white rounded-lg shadow-md p-6 mb-6">
                <p class="text-sm text-gray-500 mb-2">Timestamp: {{ entry.timestamp }}</p>
                {% if entry.error %}
                <p class="error font-semibold">Error: {{ entry.error }}</p>
                {% endif %}
                <h2 class="text-lg font-semibold text-gray-700 mb-3">Building Status</h2>
                <table class="w-full border-collapse">
                    <thead>
                        <tr class="bg-gray-50">
                            <th class="border border-gray-200 px-4 py-2 text-left text-sm font-semibold text-gray-600">Section</th>
                            <th class="border border-gray-200 px-4 py-2 text-left text-sm font-semibold text-gray-600">Details</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="border border-gray-200 px-4 py-2 text-sm text-gray-600">Summary</td>
                            <td class="border border-gray-200 px-4 py-2 text-sm text-gray-800">{{ entry.status.summary }}</td>
                        </tr>
                        <tr>
                            <td class="border border-gray-200 px-4 py-2 text-sm text-gray-600">Abnormalities</td>
                            <td class="border border-gray-200 px-4 py-2 text-sm {% if entry.status.abnormalities|length > 0 %}text-red-600{% else %}text-green-600{% endif %}">
                                {% if entry.status.abnormalities %}
                                    {% if entry.status.abnormalities is mapping %}
                                        {% for equipment, details in entry.status.abnormalities.items() %}
                                            <strong>{{ equipment }}:</strong><br>
                                            {% for key, value in details.items() %}
                                                {{ key }}: {{ value }}<br>
                                            {% endfor %}
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
                            <td class="border border-gray-200 px-4 py-2 text-sm text-gray-600">Recommendations</td>
                            <td class="border border-gray-200 px-4 py-2 text-sm text-gray-800">
                                {% if entry.status.recommendations %}
                                    {% if entry.status.recommendations is mapping %}
                                        {% for equipment, details in entry.status.recommendations.items() %}
                                            <strong>{{ equipment }}:</strong><br>
                                            {% if details is string %}
                                                {{ details }}
                                            {% else %}
                                                <ul class="list-disc pl-4">
                                                {% for rec in details %}
                                                    <li>{{ rec }}</li>
                                                {% endfor %}
                                                </ul>
                                            {% endif %}
                                            <br>
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
            <hr class="border-gray-300 my-4">
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
                    div.className = 'data-card bg-white rounded-lg shadow-md p-6 mb-6';
                    div.innerHTML = `
                        <p class="text-sm text-gray-500 mb-2">Timestamp: ${newEntry.timestamp}</p>
                        ${newEntry.error ? `<p class="error font-semibold">Error: ${newEntry.error}</p>` : ''}
                        <h2 class="text-lg font-semibold text-gray-700 mb-3">Building Status</h2>
                        <table class="w-full border-collapse">
                            <thead>
                                <tr class="bg-gray-50">
                                    <th class="border border-gray-200 px-4 py-2 text-left text-sm font-semibold text-gray-600">Section</th>
                                    <th class="border border-gray-200 px-4 py-2 text-left text-sm font-semibold text-gray-600">Details</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td class="border border-gray-200 px-4 py-2 text-sm text-gray-600">Summary</td>
                                    <td class="border border-gray-200 px-4 py-2 text-sm text-gray-800">${newEntry.status.summary}</td>
                                </tr>
                                <tr>
                                    <td class="border border-gray-200 px-4 py-2 text-sm text-gray-600">Abnormalities</td>
                                    <td class="border border-gray-200 px-4 py-2 text-sm ${newEntry.status.abnormalities.length > 0 ? 'text-red-600' : 'text-green-600'}">
                                        ${newEntry.status.abnormalities.length > 0 ? (
                                            Array.isArray(newEntry.status.abnormalities) ?
                                                `<ul class="list-disc pl-4">${newEntry.status.abnormalities.map(item => `<li>${item}</li>`).join('')}</ul>` :
                                                Object.entries(newEntry.status.abnormalities).map(([equip, details]) => `
                                                    <strong>${equip}:</strong><br>
                                                    ${Object.entries(details).map(([k, v]) => `${k}: ${v}<br>`).join('')}
                                                `).join('')
                                        ) : 'None'}
                                    </td>
                                </tr>
                                <tr>
                                    <td class="border border-gray-200 px-4 py-2 text-sm text-gray-600">Recommendations</td>
                                    <td class="border border-gray-200 px-4 py-2 text-sm text-gray-800">
                                        ${newEntry.status.recommendations.length > 0 ? (
                                            Array.isArray(newEntry.status.recommendations) ?
                                                `<ul class="list-disc pl-4">${newEntry.status.recommendations.map(item => `<li>${item}</li>`).join('')}</ul>` :
                                                Object.entries(newEntry.status.recommendations).map(([equip, details]) => `
                                                    <strong>${equip}:</strong><br>
                                                    ${typeof details === 'string' ? details :
                                                      `<ul class="list-disc pl-4">${details.map(rec => `<li>${rec}</li>`).join('')}</ul>`}
                                                    <br>
                                                `).join('')
                                        ) : 'None'}
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    `;
                    container.insertBefore(div, container.firstChild);
                    const hr = document.createElement('hr');
                    hr.className = 'border-gray-300 my-4';
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
    """Render dashboard with historical data."""
    global data_store
    data_store = load_data_store()
    print("📥 Dashboard hit — latest:", data_store[:2])
    processed_data = []
    for entry in data_store:
        try:
            status = json.loads(entry["status"]) if entry["status"] else {}
            if isinstance(status, dict) and "summary" in status:
                summary_str = status["summary"].strip()
                if summary_str.startswith("```json\n") and summary_str.endswith("\n```"):
                    summary_str = summary_str[8:-4]
                status = json.loads(summary_str)
            else:
                status = {"summary": "No data available", "abnormalities": [], "recommendations": []}
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
    """Return the latest data entry for AJAX updates."""
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
        if isinstance(status, dict) and "summary" in status:
            summary_str = status["summary"].strip()
            if summary_str.startswith("```json\n") and summary_str.endswith("\n```"):
                summary_str = summary_str[8:-4]
            status = json.loads(summary_str)
        else:
            status = {"summary": "No data available", "abnormalities": [], "recommendations": []}
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        print(f"⚠️ Error parsing latest status: {e}")
        status = {"summary": "Error parsing data", "abnormalities": [], "recommendations": []}
        entry["error"] = f"Parsing error: {str(e)}"
    return json.dumps({"status": status, "timestamp": entry["timestamp"], "error": entry.get("error")})

@app.route("/debug")
def debug():
    """Return raw data_store for debugging."""
    try:
        with open(DATA_FILE, "r") as f:
            return f"<pre>{json.dumps(json.load(f), indent=2)}</pre>"
    except Exception as e:
        return f"Error reading data_store: {str(e)}"

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
