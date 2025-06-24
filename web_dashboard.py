from flask import Flask, render_template_string
import threading, time, json, os
from data_simulator import simulate
from ai_diagnosis import analyze

app = Flask(__name__)

# File-based storage for data_store
DATA_FILE = "/tmp/building_data.json"

def load_data_store():
    """Load data_store from file or initialize if not exists."""
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"status": "Starting…", "timestamp": None, "error": None}

def save_data_store(data):
    """Save data_store to file."""
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"❌ Error saving data_store: {e}")

# Initialize data_store
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
            # Store result as JSON string
            data_store["status"] = json.dumps(result) if isinstance(result, dict) else str(result)
            data_store["timestamp"] = data.get("timestamp") or time.strftime("%Y-%m-%dT%H:%M:%SZ")
            data_store["error"] = None
            save_data_store(data_store)
        except Exception as e:
            print("❌ Error in worker:", e)
            data_store["status"] = "Error occurred"
            data_store["error"] = str(e)
            data_store["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
            save_data_store(data_store)
        time.sleep(60)

print("Starting worker thread...")
thread = threading.Thread(target=worker, daemon=True)
thread.start()

# HTML template with improved JSON formatting
TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Building AI Dashboard</title>
    <meta http-equiv="refresh" content="60"> <!-- Refresh every 60 seconds -->
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        .timestamp { color: #555; }
        .error { color: red; font-weight: bold; }
        pre { 
            background: #f4f4f4; 
            padding: 15px; 
            border-radius: 5px; 
            white-space: pre-wrap; 
            word-wrap: break-word; 
            font-size: 14px;
            line-height: 1.5;
        }
    </style>
</head>
<body>
    <h1>Building AI Dashboard</h1>
    <p class="timestamp"><strong>Last run:</strong> {{ ts }}</p>
    {% if error %}
    <p class="error"><strong>Error:</strong> {{ error }}</p>
    {% endif %}
    <h2>Building Status</h2>
    <pre>{{ formatted_status | safe }}</pre>
</body>
</html>
"""

@app.route("/")
def index():
    """Render dashboard with latest data."""
    global data_store
    data_store = load_data_store()
    print("📥 Dashboard hit — latest:", data_store)
    try:
        # Parse status as JSON
        status = json.loads(data_store["status"]) if data_store["status"] else {}
        # Extract inner JSON from summary field, removing ```json markers
        if isinstance(status, dict) and "summary" in status:
            # Remove ```json and ``` markers
            summary_str = status["summary"].strip()
            if summary_str.startswith("```json\n") and summary_str.endswith("\n```"):
                summary_str = summary_str[8:-4]
            formatted_status = json.dumps(json.loads(summary_str), indent=2)
        else:
            formatted_status = json.dumps(status, indent=2)
    except (json.JSONDecodeError, ValueError) as e:
        formatted_status = data_store["status"] or "No data available"
        data_store["error"] = f"Failed to parse status: {str(e)}"
    return render_template_string(
        TEMPLATE,
        formatted_status=formatted_status,
        ts=data_store["timestamp"],
        error=data_store.get("error")
    )

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
