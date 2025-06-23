import random, datetime, json

def simulate():
    return {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "building": "Demo Tower",
        "equipment": {
            "Chiller01": {"supplyTemp": random.uniform(40, 50), "returnTemp": random.uniform(50, 60), "valvePos": random.uniform(0, 100)},
            "AHU03": {"supplyAirTemp": random.uniform(65, 75), "fanRPM": random.uniform(1000, 2000), "damperPos": random.uniform(0, 100)},
        }
    }

if __name__ == "__main__":
    print(json.dumps(simulate(), indent=2))
