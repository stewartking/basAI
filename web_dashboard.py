from flask import Flask, render_template_string, request, redirect, url_for
import threading, time, json, os
from data_simulator import simulate
from ai_diagnosis import analyze

app = Flask(__name__, static_folder="static")

# File-based storage for data history and clients
DATA_FILE = "/tmp/building_data_history.json"
CLIENTS_FILE = "clients.json"
MAX_HISTORY = 20

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

def load_clients():
    try:
        with open(CLIENTS_FILE, "r") as f:
            data = json.load(f)
            return data.get("clients", []) if isinstance(data, dict) else []
    except (FileNotFoundError, json.JSONDecodeError, IOError) as e:
        print(f"⚠️ Error loading clients: {e}")
        return []

data_store = load_data_store()
clients = load_clients()

def safe_json_dump(obj, indent=None, max_length=500):
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
    try:
        result = []
        if isinstance(abnormalities, list):
            for ab in abnormalities:
                if isinstance(ab, dict) and "component" in ab and "issue" in ab:
                    value = f" ({ab.get('value', '')}{', normal range: ' + ab['normalRange'] if 'normalRange' in ab else ''})"
                    result.append(f"{ab['component']}: {ab['issue']}{value}")
        
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
    try:
        result = []
        if isinstance(recommendations, list):
            for rec in recommendations:
                if isinstance(rec, dict) and "action" in rec:
                    priority = f" (Priority: {rec.get('priority', 'N/A')})"
                    result.append(f"{rec['action']}{priority}")
        
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

# Homepage template
HOME_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Building AI Dashboard - Login</title>
    <meta charset="UTF-8">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { font-family: 'Inter', sans-serif; }
        .error { color: #ef4444; }
    </style>
</head>
<body class="bg-gray-50">
    <div class="max-w-md mx-auto mt-16 p-6 bg-white shadow-lg rounded-lg">
        <div class="flex items-center mb-6">
            <img src="{{ url_for('static', filename='logo.png') }}" alt="Company Logo" class="h-10 w-auto" onerror="this.src='https://via.placeholder.com/150x50?text=Your+Logo'">
            <h1 class="text-xl font-bold text-gray-900 ml-3">Building AI Dashboard</h1>
        </div>
        <h2 class="text-lg font-semibold text-gray-800 mb-4">Enter Client Code</h2>
        <form method="POST" action="{{ url_for('login') }}">
            <input type="text" name="client_code" placeholder="Enter your client code" class="w-full p-2 border border-gray-300 rounded-md mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500">
            {% if error %}
            <p class="error text-sm mb-4">{{ error }}</p>
            {% endif %}
            <button type="submit" class="w-full bg-blue-600 text-white p-2 rounded-md hover:bg-blue-700 transition">Login</button>
        </form>
    </div>
</body>
</html>
"""

# Dashboard template
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Building AI Dashboard - {{ building }}</title>
    <meta charset="UTF-8">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: 'Inter', sans-serif; }
        .data-card { transition: all 0.3s ease; border-radius: 1rem; background: linear-gradient(to bottom, #ffffff, #f8fafc); }
        .data-card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.15); }
        .error { color: #ef4444; }
        th, td { padding: 1rem; }
        .summary-text { line-height: 1.6; font-size: 0.95rem; }
        .timestamp { font-size: 0.85rem; color: #6b7280; }
        .alert { background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 0.75rem; margin-bottom: 1rem; }
        .status-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 0.5rem; }
    </style>
</head>
<body class="bg-blue-50">
    <div class="max-w-5xl mx-auto p-6">
        <div class="mb-6 flex items-center justify-between">
            <div class="flex items-center">
                <img src="{{ url_for('static', filename='logo.png') }}" alt="Company Logo" class="h-12 w-auto" onerror="this.src='https://via.placeholder.com/150x50?text=Your+Logo'">
                <h1 class="text-2xl font-bold text-gray-900 ml-4">Building AI Dashboard - {{ building }}</h1>
            </div>
            <a href="{{ url_for('index') }}" class="text-blue-600 hover:underline">Logout</a>
        </div>
        <div class="mb-4 flex items-center">
            <label for="system-filter" class="text-sm font-medium text-gray-700 mr-2">Filter System:</label>
            <select id="system-filter" class="p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="all">All Systems</option>
                <option value="chiller">Chiller</option>
                <option value="boiler">Boiler</option>
                <option value="ahu">Air Handlers</option>
            </select>
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
                    <h2 class="text-lg font-semibold text-gray-800 mb-3">
                        <span class="status-dot" style="background-color: {% if entry.status.abnormalities|length > 0 %}#ef4444{% else %}#22c55e{% endif %}"></span>
                        Building Status
                    </h2>
                    <table class="w-full border-collapse">
                        <thead>
                            <tr class="bg-gray-100">
                                <th class="border border-gray-200 text-left text-sm font-semibold text-gray-700">Section</th>
                                <th class="border border-gray-200 text-left text-sm font-semibold text-gray-700">Details</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr class="system-row" data-system="all chiller">
                                <td class="border border-gray-200 text-sm font-medium text-gray-600">Chiller Summary</td>
                                <td class="border border-gray-200 text-sm text-gray-800 summary-text">
                                    {{ entry.status.summary | regex_replace('^(Chiller:[^.]*)\\.', '\\1') | default('No chiller data') }}
                                </td>
                            </tr>
                            <tr class="system-row" data-system="all boiler">
                                <td class="border border-gray-200 text-sm font-medium text-gray-600">Boiler Summary</td>
                                <td class="border border-gray-200 text-sm text-gray-800 summary-text">
                                    {{ entry.status.summary | regex_replace('.*(Boiler:[^.]*)\\.', '\\1') | default('No boiler data') }}
                                </td>
                            </tr>
                            <tr class="system-row" data-system="all ahu">
                                <td class="border border-gray-200 text-sm font-medium text-gray-600">AHU Summary</td>
                                <td class="border border-gray-200 text-sm text-gray-800 summary-text">
                                    {{ entry.status.summary | regex_replace('.*(Air Handlers:[^.]*)\\.', '\\1') | default('No AHU data') }}
                                </td>
                            </tr>
                            <tr class="system-row" data-system="all">
                                <td class="border border-gray-200 text-sm font-medium text-gray-600">Abnormalities</td>
                                <td class="border border-gray-200 text-sm {% if entry.status.abnormalities|length > 0 %}text-red-600{% else %}text-green-600{% endif %}">
                                    {% if entry.status.abnormalities %}
                                        <ul class="list-disc pl-4">
                                            {% for item in entry.status.abnormalities %}
                                                <li class="abnormality" data-system="{% if 'Compressor' in item %}chiller{% elif 'Boiler' in item %}boiler{% elif 'AHU' in item %}ahu{% else %}all{% endif %}">{{ item }}</li>
                                            {% endfor %}
                                        </ul>
                                    {% else %}
                                        None
                                    {% endif %}
                                </td>
                            </tr>
                            <tr class="system-row" data-system="all">
                                <td class="border border-gray-200 text-sm font-medium text-gray-600">Recommendations</td>
                                <td class="border border-gray-200 text-sm text-gray-800">
                                    {% if entry.status.recommendations %}
                                        <ul class="list-disc pl-4">
                                            {% for item in entry.status.recommendations %}
                                                <li class="recommendation" data-system="{% if 'chiller' in item|lower %}chiller{% elif 'boiler' in item|lower %}boiler{% elif 'ahu' in item|lower %}ahu{% else %}all{% endif %}">{{ item }}</li>
                                            {% endfor %}
                                        </ul>
                                    {% else %}
                                        None
                                    {% endif %}
                                </td>
                            </tr>
                        </tbody>
                    </table>
                    <canvas id="pressureChart-{{ loop.index }}" class="mt-4" style="max-height: 200px;"></canvas>
                </div>
            </div>
            <hr class="border-gray-200 my-4">
            {% endfor %}
        </div>
    </div>
    <script>
        // Filter system rows
        document.getElementById('system-filter').addEventListener('change', function() {
            const filter = this.value;
            document.querySelectorAll('.system-row').forEach(row => {
                const systems = row.getAttribute('data-system').split(' ');
                row.style.display = systems.includes(filter) || filter === 'all' ? '' : 'none';
            });
            document.querySelectorAll('.abnormality, .recommendation').forEach(item => {
                const system = item.getAttribute('data-system');
                item.style.display = system === filter || filter === 'all' ? '' : 'none';
            });
        });

        // Render charts
        {% for entry in data_store %}
        try {
            const rawData = {{ entry.raw_data | safe }};
            const ctx = document.getElementById('pressureChart-{{ loop.index }}').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: ['Compressor01', 'Compressor02', 'Compressor03'],
                    datasets: [{
                        label: 'Discharge Pressure (psig)',
                        data: [
                            rawData.equipment?.ChillerSystem?.Compressor01?.dischargePressure || 0,
                            rawData.equipment?.ChillerSystem?.Compressor02?.dischargePressure || 0,
                            rawData.equipment?.ChillerSystem?.Compressor03?.dischargePressure || 0
                        ],
                        borderColor: '#3b82f6',
                        fill: false
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: false, suggestedMin: 300, suggestedMax: 400 }
                    }
                }
            });
        } catch (e) {
            console.error('Chart error:', e);
        }
        {% endfor %}

        // Fetch new data
        async function fetchNewData() {
            try {
                const response = await fetch('/latest/{{ client_code }}');
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
                            <h2 class="text-lg font-semibold text-gray-800 mb-3">
                                <span class="status-dot" style="background-color: ${newEntry.status.abnormalities.length > 0 ? '#ef4444' : '#22c55e'}"></span>
                                Building Status
                            </h2>
                            <table class="w-full border-collapse">
                                <thead>
                                    <tr class="bg-gray-100">
                                        <th class="border border-gray-200 text-left text-sm font-semibold text-gray-700">Section</th>
                                        <th class="border border-gray-200 text-left text-sm font-semibold text-gray-700">Details</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr class="system-row" data-system="all chiller">
                                        <td class="border border-gray-200 text-sm font-medium text-gray-600">Chiller Summary</td>
                                        <td class="border border-gray-200 text-sm text-gray-800 summary-text">${newEntry.status.summary.match(/(Chiller:[^.]*)\\.?/)?.[1] || 'No chiller data'}</td>
                                    </tr>
                                    <tr class="system-row" data-system="all boiler">
                                        <td class="border border-gray-200 text-sm font-medium text-gray-600">Boiler Summary</td>
                                        <td class="border border-gray-200 text-sm text-gray-800 summary-text">${newEntry.status.summary.match(/(Boiler:[^.]*)\\.?/)?.[1] || 'No boiler data'}</td>
                                    </tr>
                                    <tr class="system-row" data-system="all ahu">
                                        <td class="border border-gray-200 text-sm font-medium text-gray-600">AHU Summary</td>
                                        <td class="border border-gray-200 text-sm text-gray-800 summary-text">${newEntry.status.summary.match(/(Air Handlers:[^.]*)\\.?/)?.[1] || 'No AHU data'}</td>
                                    </tr>
                                    <tr class="system-row" data-system="all">
                                        <td class="border border-gray-200 text-sm font-medium text-gray-600">Abnormalities</td>
                                        <td class="border border-gray-200 text-sm ${newEntry.status.abnormalities.length > 0 ? 'text-red-600' : 'text-green-600'}">
                                            ${newEntry.status.abnormalities.length > 0 ? `
                                                <ul class="list-disc pl-4">
                                                    ${newEntry.status.abnormalities.map(item => `<li class="abnormality" data-system="${item.includes('Compressor') ? 'chiller' : item.includes('Boiler') ? 'boiler' : item.includes('AHU') ? 'ahu' : 'all'}">${item}</li>`).join('')}
                                                </ul>
                                            ` : 'None'}
                                        </td>
                                    </tr>
                                    <tr class="system-row" data-system="all">
                                        <td class="border border-gray-200 text-sm font-medium text-gray-600">Recommendations</td>
                                        <td class="border border-gray-200 text-sm text-gray-800">
                                            ${newEntry.status.recommendations.length > 0 ? `
                                                <ul class="list-disc pl-4">
                                                    ${newEntry.status.recommendations.map(item => `<li class="recommendation" data-system="${item.toLowerCase().includes('chiller') ? 'chiller' : item.toLowerCase().includes('boiler') ? 'boiler' : item.toLowerCase().includes('ahu') ? 'ahu' : 'all'}">${item}</li>`).join('')}
                                                </ul>
                                            ` : 'None'}
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                            <canvas id="pressureChart-new" class="mt-4" style="max-height: 200px;"></canvas>
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
                    try {
                        const ctx = document.getElementById('pressureChart-new').getContext('2d');
                        new Chart(ctx, {
                            type: 'line',
                            data: {
                                labels: ['Compressor01', 'Compressor02', 'Compressor03'],
                                datasets: [{
                                    label: 'Discharge Pressure (psig)',
                                    data: [
                                        newEntry.raw_data?.equipment?.ChillerSystem?.Compressor01?.dischargePressure || 0,
                                        newEntry.raw_data?.equipment?.ChillerSystem?.Compressor02?.dischargePressure || 0,
                                        newEntry.raw_data?.equipment?.ChillerSystem?.Compressor03?.dischargePressure || 0
                                    ],
                                    borderColor: '#3b82f6',
                                    fill: false
                                }]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                scales: {
                                    y: { beginAtZero: false, suggestedMin: 300, suggestedMax: 400 }
                                }
                            }
                        });
                    } catch (e) {
                        console.error('Chart error:', e);
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

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        client_code = request.form.get("client_code")
        for client in clients:
            if client["code"] == client_code:
                return redirect(url_for("dashboard", client_code=client_code))
        return render_template_string(HOME_TEMPLATE, error="Invalid client code")
    return render_template_string(HOME_TEMPLATE, error=None)

@app.route("/dashboard/<client_code>")
def dashboard(client_code):
    global data_store, clients
    data_store = load_data_store()
    client = next((c for c in clients if c["code"] == client_code), None)
    if not client:
        return redirect(url_for("index"))
    
    building = client["building"]
    filtered_data = [entry for entry in data_store if json.loads(entry.get("raw_data", "{}")).get("building") == building]
    print(f"📥 Dashboard hit for {building} — latest:", safe_json_dump(filtered_data[:2], indent=2))
    
    processed_data = []
    for entry in filtered_data:
        try:
            status = json.loads(entry["status"]) if entry["status"] else {}
            raw_data = json.loads(entry.get("raw_data", "{}"))
            summary = status.get("summary", "No summary available")
            abnormalities = status.get("abnormalities", [])
            recommendations = status.get("recommendations", [])
            
            if isinstance(summary, str) and summary.startswith("```json\n") and summary.endswith("\n```"):
                try:
                    nested_data = json.loads(summary[8:-4])
                    if isinstance(nested_data, dict):
                        summary = nested_data.get("summary", summary)
                        abnormalities = nested_data.get("abnormalities", abnormalities)
                        recommendations = nested_data.get("recommendations", recommendations)
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"⚠️ Error parsing JSON code block: {e}")
            
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
            processed_data.append({
                "status": status,
                "timestamp": entry["timestamp"],
                "error": entry.get("error"),
                "raw_data": raw_data
            })
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            print(f"⚠️ Error parsing status for timestamp {entry['timestamp']}: {e}")
            processed_data.append({
                "status": {"summary": "Error parsing data", "abnormalities": [], "recommendations": []},
                "timestamp": entry["timestamp"],
                "error": f"Parsing error: {str(e)}",
                "raw_data": {}
            })
    
    return render_template_string(DASHBOARD_TEMPLATE, data_store=processed_data, building=building, client_code=client_code, MAX_HISTORY=MAX_HISTORY)

@app.route("/latest/<client_code>")
def latest(client_code):
    global data_store, clients
    data_store = load_data_store()
    client = next((c for c in clients if c["code"] == client_code), None)
    if not client:
        return json.dumps({"error": "Invalid client code"}), 403
    
    building = client["building"]
    filtered_data = [entry for entry in data_store if json.loads(entry.get("raw_data", "{}")).get("building") == building]
    if not filtered_data:
        return json.dumps({
            "status": {"summary": "No data available", "abnormalities": [], "recommendations": []},
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "error": "No data available",
            "raw_data": {}
        })
    
    entry = filtered_data[0]
    try:
        status = json.loads(entry["status"]) if entry["status"] else {}
        raw_data = json.loads(entry.get("raw_data", "{}"))
        summary = status.get("summary", "No summary available")
        abnormalities = status.get("abnormalities", [])
        recommendations = status.get("recommendations", [])
        
        if isinstance(summary, str) and summary.startswith("```json\n") and summary.endswith("\n```"):
            try:
                nested_data = json.loads(summary[8:-4])
                if isinstance(nested_data, dict):
                    summary = nested_data.get("summary", summary)
                    abnormalities = nested_data.get("abnormalities", abnormalities)
                    recommendations = nested_data.get("recommendations", recommendations)
            except (json.JSONDecodeError, ValueError) as e:
                print(f"⚠️ Error parsing JSON code block: {e}")
        
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
    
    return json.dumps({
        "status": status,
        "timestamp": entry["timestamp"],
        "error": entry.get("error"),
        "raw_data": raw_data
    })

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
