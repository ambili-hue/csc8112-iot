import os, time, json, uuid, requests
import paho.mqtt.client as mqtt

SENSOR_URL = os.getenv("SENSOR_URL", "http://smartcam.uo.ncl.ac.uk:8001/sensor")
CAMERA_URL = os.getenv("CAMERA_URL", "http://smartcam.uo.ncl.ac.uk:8001/camera")
MQTT_HOST  = os.getenv("MQTT_HOST", "mosquitto")
CHUNK = 32 * 1024          # split large images into 32 KB pieces (Task 1 hint)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
while True:                # wait until the broker is up
    try: client.connect(MQTT_HOST, 1883); break
    except Exception: print("waiting for MQTT..."); time.sleep(2)
client.loop_start()
seen = set()               # data loops every 9 min, so don't resend old readings

while True:
    # (a) GET sensor JSON, (d) keep only PM2.5 Timestamp + Value
    try:
        for r in requests.get(SENSOR_URL, timeout=10).json():
            if str(r.get("Variable", "")).upper() != "PM2.5": continue
            ts, val = r["Timestamp"], float(r["Value"])
            if ts in seen: continue
            seen.add(ts)
            if val > 50:                       # (d) outlier filter
                print(f"OUTLIER  {ts}  {val}"); continue
            # (e) send PM2.5 for Task 3/4
            client.publish("iot/pm25", json.dumps({"Timestamp": ts, "Value": val}))
            print(f"PM2.5 sent {ts} {val}")
    except Exception as e: print("sensor error:", e)

    # (b) GET camera JPEG, (f) send for Task 2 in chunks
    try:
        img = requests.get(CAMERA_URL, timeout=10).content
        fid, total = uuid.uuid4().hex[:8], (len(img) + CHUNK - 1) // CHUNK
        for i in range(total):
            header = f"{fid}|{i}|{total}\n".encode()
            client.publish("iot/camera", header + img[i*CHUNK:(i+1)*CHUNK])
        print(f"frame {fid} sent in {total} chunk(s), {len(img)} bytes")
    except Exception as e: print("camera error:", e)

    time.sleep(5)                              # (c) poll every 5 seconds