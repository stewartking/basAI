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
            # Ensure result is JSON-serializable
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

# Start worker thread
print("Starting worker thread...")
thread = threading.Thread(target=worker, daemon=True)
thread.start()

# HTML template with auto-refresh
TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Building AI Dashboard</title>
    <meta http-equiv="refresh" content="60"> <!-- Refresh every 60 seconds -->
    <style>
        pre { background: #f4f4f4; padding: 10px; border-radius: 5px; }
        .error { color: red; }
    </style>
</head>
<body>
    <h1>Building AI Dashboard</h1>
    <p><strong>Last run:</strong> {{ ts }}</p>
    {% if error %}
    <p class="error"><strong>Error:</strong> {{ error }}</p>
    {% endif %}
    <h2>Building Status</h2>
    <pre>{{ status | safe }}</pre>
</body>
</html>
"""

@app.route("/")
def index():
    """Render dashboard with latest data."""
    # Reload data_store to ensure latest data (optional for robustness)
    global data_store
    data_store = load_data_store()
    print("📥 Dashboard hit — latest:", data_store)
    try:
        # Parse status as JSON if possible
        status = json.loads(data_store["status"]) if data_store["status"] else "No data"
    except json.JSONDecodeError:
        status = data_store["status"]
    return render_template_string(
        TEMPLATE,
        status=status,
        ts=data_store["timestamp"],
        error=data_store.get("error")
    )

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

