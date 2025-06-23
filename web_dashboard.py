from flask import Flask, render_template_string
import threading, time, json
from data_simulator import simulate
from ai_diagnosis import analyze
import os

app = Flask(__name__)
latest = {"status": "Starting…", "timestamp": None}

def worker():
    while True:
        print("🚀 Worker running...")
        data = simulate()
        print("📡 Simulated data:", data)
        result = analyze(data)
        print("🧠 AI result:", result)

        summary = result.get("summary", "")
        summary = summary.strip("`").replace("```json", "").replace("```", "").strip()
        latest["status"] = summary
        latest["timestamp"] = data["timestamp"]

        time.sleep(60)


# ✅ Start the background AI processing loop immediately
threading.Thread(target=worker, daemon=True).start()

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
    print("📥 Dashboard hit — latest:", latest)
    return render_template_string(TEMPLATE, status=latest["status"], ts=latest["timestamp"])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


