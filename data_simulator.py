import random
import datetime
import json
import math

def simulate():
    """Simulate complex BAS data for a building with chiller, boiler, AHUs, and VAVs."""
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    building = "Demo Tower"

    # Helper function for R-134a pressure-temperature relationship (approximate)
    def temp_to_pressure(temp_f):
        """Convert temperature (°F) to R-134a saturation pressure (psig)."""
        temp_c = (temp_f - 32) * 5 / 9
        # Simplified Antoine equation for R-134a
        pressure_kpa = math.exp(16.528 - 3640.2 / (temp_c + 240.97)) * 100
        pressure_psig = (pressure_kpa * 0.145038) - 14.696  # Convert kPa to psig
        return max(0, round(pressure_psig, 1))

    # Chiller system (6 Turbocor compressors, R-134a, plate-and-frame HXs)
    chiller = {}
    chilled_water_supply_temp = random.uniform(42, 46)  # °F
    chilled_water_return_temp = chilled_water_supply_temp + random.uniform(8, 12)  # ΔT
    condenser_water_supply_temp = random.uniform(78, 85)  # °F (from cooling tower)
    condenser_water_return_temp = condenser_water_supply_temp + random.uniform(8, 12)  # ΔT
    cooling_tower_fan_speed = random.uniform(60, 100)  # % (variable speed)
    cooling_tower_water_temp = condenser_water_supply_temp - random.uniform(2, 5)  # Approach temp
    chilled_water_flow = random.uniform(800, 1200)  # GPM (total for chiller)
    condenser_water_flow = random.uniform(1000, 1500)  # GPM

    for i in range(1, 7):
        comp_name = f"Compressor0{i}"
        # Normal operating conditions
        evap_temp = chilled_water_supply_temp - random.uniform(4, 6)  # °F
        suction_pressure = temp_to_pressure(evap_temp)  # psig
        condenser_temp = condenser_water_supply_temp + random.uniform(5, 10)  # °F
        discharge_pressure = temp_to_pressure(condenser_temp)  # psig
        power = random.uniform(150, 250)  # kW (Turbocor typical)
        exv_position = random.uniform(30, 80)  # % open
        # Introduce head pressure issues for compressors 1–3
        if i <= 3:
            discharge_pressure += random.uniform(30, 50)  # Elevated (180–200 psig)
            power += random.uniform(20, 40)  # Increased due to higher load
            exv_position = min(100, exv_position + random.uniform(10, 20))  # Compensating
        chiller[comp_name] = {
            "suctionPressure": round(suction_pressure, 1),  # psig
            "dischargePressure": round(discharge_pressure, 1),  # psig
            "power": round(power, 1),  # kW
            "exvPosition": round(exv_position, 1),  # %
            "status": "Running"
        }
    chiller.update({
        "chilledWaterSupplyTemp": round(chilled_water_supply_temp, 1),  # °F
        "chilledWaterReturnTemp": round(chilled_water_return_temp, 1),  # °F
        "condenserWaterSupplyTemp": round(condenser_water_supply_temp, 1),  # °F
        "condenserWaterReturnTemp": round(condenser_water_return_temp, 1),  # °F
        "chilledWaterFlow": round(chilled_water_flow, 1),  # GPM
        "condenserWaterFlow": round(condenser_water_flow, 1),  # GPM
        "coolingTowerFanSpeed": round(cooling_tower_fan_speed, 1),  # %
        "coolingTowerWaterTemp": round(cooling_tower_water_temp, 1)  # °F
    })

    # Boiler system (3 atmospheric boilers)
    boilers = {}
    hot_water_supply_temp = random.uniform(160, 180)  # °F
    hot_water_return_temp = hot_water_supply_temp - random.uniform(15, 25)  # ΔT
    hot_water_flow = random.uniform(200, 400)  # GPM
    for i in range(1, 4):
        boiler_name = f"Boiler0{i}"
        burner_status = random.choice(["On", "Off"]) if i <= 2 else "Off"  # Lead/lag staging
        fuel_flow = random.uniform(50, 100) if burner_status == "On" else 0  # Therms/hour
        boilers[boiler_name] = {
            "burnerStatus": burner_status,
            "fuelFlow": round(fuel_flow, 1),  # Therms/hour
            "supplyTemp": round(hot_water_supply_temp, 1) if burner_status == "On" else round(hot_water_return_temp, 1),
            "returnTemp": round(hot_water_return_temp, 1)
        }
    boilers.update({
        "hotWaterSupplyTemp": round(hot_water_supply_temp, 1),  # °F
        "hotWaterReturnTemp": round(hot_water_return_temp, 1),  # °F
        "hotWaterFlow": round(hot_water_flow, 1),  # GPM
        "pumpStatus": "On"
    })

    # AHUs and VAVs (10 floors)
    floors = {}
    for floor in range(1, 11):
        ahu_name = f"AHU-Floor{floor:02d}"
        supply_air_temp = random.uniform(55, 65)  # °F
        return_air_temp = supply_air_temp + random.uniform(8, 12)  # °F
        fan_speed = random.uniform(1000, 1800)  # RPM
        static_pressure = random.uniform(1.5, 2.5)  # in. w.c.
        outside_air_damper = random.uniform(10, 30)  # % open
        # Simulate 5–10 VAV boxes per floor
        vav_boxes = {}
        num_vavs = random.randint(5, 10)
        for vav in range(1, num_vavs + 1):
            vav_name = f"VAV{floor:02d}-{vav:02d}"
            zone_temp = random.uniform(68, 74)  # °F
            damper_pos = random.uniform(20, 80)  # % open
            reheat_valve = random.uniform(0, 50) if zone_temp < 70 else 0  # % open
            airflow = random.uniform(200, 800)  # CFM
            vav_boxes[vav_name] = {
                "zoneTemp": round(zone_temp, 1),  # °F
                "damperPosition": round(damper_pos, 1),  # %
                "reheatValvePosition": round(reheat_valve, 1),  # %
                "airflow": round(airflow, 1)  # CFM
            }
        floors[ahu_name] = {
            "supplyAirTemp": round(supply_air_temp, 1),  # °F
            "returnAirTemp": round(return_air_temp, 1),  # °F
            "fanSpeed": round(fan_speed, 1),  # RPM
            "staticPressure": round(static_pressure, 2),  # in. w.c.
            "outsideAirDamper": round(outside_air_damper, 1),  # %
            "vavBoxes": vav_boxes
        }

    # Wall radiators (10 floors, 10 rads per floor)
    radiators = {}
    for floor in range(1, 11):
        for rad in range(1, 11):
            rad_name = f"Rad{floor:02d}-{rad:02d}"
            valve_pos = random.uniform(0, 100) if hot_water_supply_temp > 160 else 0  # % open
            space_temp = random.uniform(68, 74)  # °F
            radiators[rad_name] = {
                "valvePosition": round(valve_pos, 1),  # %
                "spaceTemp": round(space_temp, 1)  # °F
            }

    return {
        "timestamp": timestamp,
        "building": building,
        "equipment": {
            "ChillerSystem": chiller,
            "BoilerSystem": boilers,
            "AirHandlers": floors,
            "Radiators": radiators
        }
    }

if __name__ == "__main__":
    print(json.dumps(simulate(), indent=2))
