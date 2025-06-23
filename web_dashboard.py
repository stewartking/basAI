from flask import Flask, render_template_string
import threading, time
from data_simulator import simulate
from ai_diagnosis import analyze

app = Flask(__name__)

# Shared data dictionary
latest = {"status": "Starting…", "timestamp": None}

# Background worker that updates 'latest'
def worker():
    while True:
        print("🚀 Worker running...")
        data = simulate()
        print("📡 Simulated data:", data)
        result = analyze(data)
        print("🧠 AI result:", result)

        latest["status"] = result.get("summary", str(result))
        latest["timestamp"] = data.get("timestamp")

        time.sleep(60)

# Start worker as soon as app starts
threading.Thread(target=worker, daemon=True).start()

# HTML template
TEMPLATE = """
<html>
<head><title>Building AI Dashboard</title></head>
<body>
<h1>Building AI Dashboard</h1>
<p><strong>Last run:</strong> {{ ts }}</p>
<pre>{{ status }}</pre>
</body>
</html>
"""

@app.route("/")
def index():
    print(f"📥 Dashboard hit — latest: {latest}")
    return render_template_string(TEMPLATE, status=latest["status"], ts=latest["timestamp"])

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

