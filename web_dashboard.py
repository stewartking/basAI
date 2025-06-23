from flask import Flask, render_template_string
import threading, time
from data_simulator import simulate
from ai_diagnosis import analyze

app = Flask(__name__)

# ✅ Store shared data in app.config
app.config["LATEST_STATUS"] = "Starting…"
app.config["LATEST_TIMESTAMP"] = None

def worker():
    while True:
        print("🚀 Worker running...")
        data = simulate()
        print("📡 Simulated data:", data)
        result = analyze(data)
        print("🧠 AI result:", result)
        app.config["LATEST_STATUS"] = result
        app.config["LATEST_TIMESTAMP"] = data["timestamp"]
        time.sleep(60)

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
    print("📥 Dashboard hit — latest:", app.config["LATEST_STATUS"])
    return render_template_string(
        TEMPLATE,
        status=app.config["LATEST_STATUS"],
        ts=app.config["LATEST_TIMESTAMP"]
    )

# ✅ Start the worker thread
threading.Thread(target=worker, daemon=True).start()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
