import os, json, time, cv2, numpy as np
import paho.mqtt.client as mqtt
from ultralytics import YOLO

model = YOLO("yolo11n.pt")
VEHICLES = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}   # COCO class ids
parts = {}                                                    # frame_id -> chunks

def on_message(client, userdata, msg):
    # (a) receive frame chunks from Task 1 and rebuild the JPEG
    header, data = msg.payload.split(b"\n", 1)
    fid, idx, total = header.decode().split("|")
    parts.setdefault(fid, {})[int(idx)] = data
    if len(parts[fid]) < int(total): return
    jpeg = b"".join(parts.pop(fid)[i] for i in range(int(total)))
    frame = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)

    # (b) detect vehicles, draw red boxes on a second image
    result = model(frame, verbose=False)[0]
    annotated, count = frame.copy(), 0
    for box in result.boxes:
        cls = int(box.cls[0])
        if cls in VEHICLES:
            count += 1
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 2)  # red (BGR)
            cv2.putText(annotated, VEHICLES[cls], (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    # (c) publish annotated image as BYTES (not numpy) + vehicle count
    ok, buf = cv2.imencode(".jpg", annotated)
    client.publish("iot/annotated", buf.tobytes())
    client.publish("iot/vehicle_count", json.dumps({"frame_id": fid, "count": count}))
    print(f"frame {fid}: {count} vehicle(s)")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_message = on_message
while True:
    try: client.connect(os.getenv("MQTT_HOST", "mosquitto"), 1883); break
    except Exception: print("waiting for MQTT..."); time.sleep(2)
client.subscribe("iot/camera")
client.loop_forever()