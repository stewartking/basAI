# data_simulator.py (simplified)
import time
import random

def simulate():
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "building": "Demo Tower",
        "equipment": {
            "ChillerSystem": {
                "Compressor01": {
                    "dischargePressure": round(random.uniform(300, 380), 1),  # Some high pressures
                    "status": "Running"
                },
                "Compressor02": {
                    "dischargePressure": round(random.uniform(300, 380), 1),
                    "status": "Running"
                },
                "Compressor03": {
                    "dischargePressure": round(random.uniform(300, 350), 1),
                    "status": "Off"
                },
                "chilledWaterSupplyTemp": round(random.uniform(42, 46), 1),
                "coolingTowerFanSpeed": round(random.uniform(50, 80), 1)
            },
            "BoilerSystem": {
                "Boiler01": {
                    "burnerStatus": "On",
                    "supplyTemp": round(random.uniform(160, 180), 1)
                },
                "Boiler02": {
                    "burnerStatus": "Off",
                    "supplyTemp": round(random.uniform(140, 150), 1)
                },
                "hotWaterSupplyTemp": round(random.uniform(160, 175), 1),
                "pumpStatus": "On"
            },
            "AirHandlers": {
                "AHU01": {
                    "supplyAirTemp": round(random.uniform(58, 62), 1),
                    "returnAirTemp": round(random.uniform(68, 72), 1),
                    "fanSpeed": round(random.uniform(1000, 1500), 1)
                },
                "AHU02": {
                    "supplyAirTemp": round(random.uniform(58, 62), 1),
                    "returnAirTemp": round(random.uniform(68, 72), 1),
                    "fanSpeed": round(random.uniform(1000, 1500), 1)
                },
                "AHU03": {
                    "supplyAirTemp": round(random.uniform(55, 60), 1),  # Slightly low
                    "returnAirTemp": round(random.uniform(68, 72), 1),
                    "fanSpeed": round(random.uniform(1000, 1500), 1)
                }
            }
        }
    }
