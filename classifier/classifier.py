import os, json, time
from collections import Counter
import numpy as np, tensorflow as tf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import paho.mqtt.client as mqtt

OUT, BATCH = "/app/output", 20
COLOURS = {"GREEN": "green", "YELLOW": "gold", "RED": "red"}

# (a) load the TFLite model + scaler saved during training
sc = json.load(open("scaler.json"))
MEAN, STD, CLASSES = sc["mean"], sc["std"], sc["classes"]
interp = tf.lite.Interpreter(model_path="model.tflite")
inp, out = interp.get_input_details()[0], interp.get_output_details()[0]
print("Loaded model.tflite, classes:", CLASSES)

batch, history = [], []

def classify(readings):
    # (c) batch inference: one model call for the whole batch
    x = ((np.array([r["Value"] for r in readings], np.float32) - MEAN) / STD).reshape(-1, 1)
    interp.resize_tensor_input(inp["index"], x.shape); interp.allocate_tensors()
    interp.set_tensor(inp["index"], x); interp.invoke()
    return [CLASSES[i] for i in interp.get_tensor(out["index"]).argmax(axis=1)]

def save_plots():
    # (i) bar chart, colour-coded time series, frequency distribution, summary
    labels = [h["predicted_quality"] for h in history]
    values = [h["value"] for h in history]
    counts = Counter(labels); order = ["GREEN", "YELLOW", "RED"]
    plt.figure(); plt.bar(order, [counts[c] for c in order], color=[COLOURS[c] for c in order])
    plt.title("Classification counts"); plt.ylabel("Count"); plt.savefig(f"{OUT}/class_counts.png"); plt.close()
    plt.figure(figsize=(12, 4)); plt.plot(range(len(values)), values, color="lightgrey")
    plt.scatter(range(len(values)), values, c=[COLOURS[l] for l in labels], s=8)
    plt.title("PM2.5 time series, colour = predicted class"); plt.xlabel("Reading #"); plt.ylabel("PM2.5")
    plt.savefig(f"{OUT}/class_timeseries.png"); plt.close()
    plt.figure(); plt.hist(values, bins=30, color="steelblue")
    plt.title("PM2.5 frequency distribution"); plt.xlabel("PM2.5"); plt.ylabel("Frequency")
    plt.savefig(f"{OUT}/pm25_histogram.png"); plt.close()
    print(f"SUMMARY: total={len(history)} " + " ".join(f"{c}={counts[c]}" for c in order))

def on_message(client, userdata, msg):
    # (b) receive PM2.5 readings from Task 1
    batch.append(json.loads(msg.payload))
    if len(batch) < BATCH: return
    for r, label in zip(batch, classify(batch)):
        # (d) classify, (e) log to console, (f) publish for Task 5
        print(f"PM2.5={r['Value']:.3f} -> {label}")
        result = {"timestamp": r["Timestamp"], "value": r["Value"], "predicted_quality": label}
        client.publish("iot/classification", json.dumps(result))
        history.append(result)
    batch.clear()
    if len(history) % 200 == 0: save_plots()

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_message = on_message
while True:
    try: client.connect(os.getenv("MQTT_HOST", "mosquitto"), 1883); break
    except Exception: print("waiting for MQTT..."); time.sleep(2)
client.subscribe("iot/pm25")
client.loop_forever()