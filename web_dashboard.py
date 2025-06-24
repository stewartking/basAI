from flask import Flask, render_template_string
import threading, time
from data_simulator import simulate
from ai_diagnosis import analyze

app = Flask(__name__)

# Move latest inside a class to avoid scope issues
data_store = {
    "status": "Starting…",
    "timestamp": None
}

# Worker function

def worker():
    while True:
        print("🚀 Worker running...")
        try:
            data = simulate()
            print("📡 Simulated data:", data)
            result = analyze(data)
            print("🧠 AI result:", result)
            data_store["status"] = result
            data_store["timestamp"] = data.get("timestamp")
        except Exception as e:
            print("❌ Error in worker:", e)
        time.sleep(60)

# Start worker in background (outside __main__ so it runs in Gunicorn)
thread = threading.Thread(target=worker, daemon=True)
thread.start()

# HTML template
TEMPLATE = """
<html>
<head><title>Building AI Dashboard</title></head>
<body>
<h1>Building AI Dashboard</h1>
<p><strong>Last run:</strong> {{ ts }}</p>
<pre>{{ status | tojson(indent=2) }}</pre>
</body>
</html>
"""

@app.route("/")
def index():
    print("📥 Dashboard hit — latest:", data_store)
    return render_template_string(
        TEMPLATE,
        status=data_store["status"],
        ts=data_store["timestamp"]
    )

# Only for local testing; Render uses gunicorn
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

