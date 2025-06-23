from flask import Flask, render_template_string
import threading, time
from data_simulator import simulate
from ai_diagnosis import analyze

app = Flask(__name__)
latest = {"status": "Starting…", "timestamp": None}

# ✅ Worker function
def worker():
    while True:
        print("🚀 Worker running...")
        data = simulate()
        print("📡 Simulated data:", data)
        result = analyze(data)
        print("🧠 AI result:", result)
        latest["status"] = result
        latest["timestamp"] = data["timestamp"]
        time.sleep(60)

# ✅ Start worker on import (will run even in Gunicorn)
threading.Thread(target=worker, daemon=True).start()

# ✅ HTML template
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

# ✅ Flask route
@app.route("/")
def index():
    print("📥 Dashboard hit — latest:", latest)
    return render_template_string(TEMPLATE, status=latest["status"], ts=latest["timestamp"])

# ✅ Use correct port for Render
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

