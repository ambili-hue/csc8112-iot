import os, json, time, requests
import paho.mqtt.client as mqtt

DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://dashboard.cloud.ncl.ac.uk:8000/api/records")
THRESHOLD = 5

# Hint approach: keep only the LATEST image and LATEST PM2.5 result in memory
latest_image = None
latest_result = None

def on_message(client, userdata, msg):
    global latest_image, latest_result
    if msg.topic == "iot/annotated":                 # from Task 2
        latest_image = msg.payload                   # JPEG bytes
    elif msg.topic == "iot/classification":          # from Task 4
        latest_result = json.loads(msg.payload)
    elif msg.topic == "iot/vehicle_count":           # from Task 2, the TRIGGER
        count = json.loads(msg.payload)["count"]
        if count <= THRESHOLD:
            print(f"{count} vehicle(s) <= {THRESHOLD}, not sent"); return
        if latest_image is None or latest_result is None:
            print("missing image or PM2.5 result, skipped"); return
        data = {
            "timestamp": latest_result["timestamp"] / 1000,   # ms -> Unix seconds
            "value": latest_result["value"],
            "predicted_quality": latest_result["predicted_quality"],
        }
        files = {"image": ("annotated.jpg", latest_image, "image/jpeg")}
        try:
            r = requests.post(DASHBOARD_URL, data=data, files=files, timeout=10)
            print(f"{count} vehicles -> SENT {data} | HTTP {r.status_code}")
        except Exception as e:
            print("dashboard error:", e)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_message = on_message
while True:
    try: client.connect(os.getenv("MQTT_HOST", "mosquitto"), 1883); break
    except Exception: print("waiting for MQTT..."); time.sleep(2)
client.subscribe([("iot/annotated", 0), ("iot/classification", 0), ("iot/vehicle_count", 0)])
client.loop_forever()