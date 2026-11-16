import os, json, time
import pandas as pd
import matplotlib
matplotlib.use("Agg")                     # no screen in Docker, save to file
import matplotlib.pyplot as plt
import paho.mqtt.client as mqtt
from ml_engine import MLPredictor

TARGET = 8706
OUT = "/app/output"
data = []

def on_message(client, userdata, msg):
    # (a) collect PM2.5 from Task 1 until 8706 points
    data.append(json.loads(msg.payload))
    if len(data) % 500 == 0: print(f"collected {len(data)}/{TARGET}")
    if len(data) >= TARGET: client.disconnect()

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_message = on_message
while True:
    try: client.connect(os.getenv("MQTT_HOST", "mosquitto"), 1883); break
    except Exception: print("waiting for MQTT..."); time.sleep(2)
client.subscribe("iot/pm25")
client.loop_forever()

# (b) remove duplicates, sort by timestamp
df = pd.DataFrame(data).drop_duplicates().sort_values("Timestamp").reset_index(drop=True)
print(f"after dedup: {len(df)} points; last 2 values: {df['Value'].tail(2).tolist()}")

# (c) average over 10-minute periods, (d) convert timestamp and print
df["Timestamp"] = pd.to_datetime(df["Timestamp"], unit="ms")
avg = df.set_index("Timestamp").resample("10min").mean().dropna().reset_index()
avg["Timestamp"] = avg["Timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
print(avg.to_string(index=False))

# (e) line chart of averaged PM2.5 data
plt.figure(figsize=(14, 5))
plt.plot(pd.to_datetime(avg["Timestamp"]), avg["Value"])
plt.title("PM2.5 averaged over 10-minute periods"); plt.xlabel("Date"); plt.ylabel("PM2.5 (µg/m³)")
plt.grid(True); plt.tight_layout()
plt.savefig(f"{OUT}/pm25_averaged.png"); print("saved pm25_averaged.png")

# (f) feed to the ML engine (Prophet) and predict
avg["Timestamp"] = pd.to_datetime(avg["Timestamp"])
predictor = MLPredictor(avg.copy())
predictor.train()
forecast = predictor.predict()
print("Next 2 hours (12 x 10 min):")
print(forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(15).head(12).to_string(index=False))

# (i) save the ML engine's own prediction plot to the bind mount
predictor.plot_result(forecast).savefig(f"{OUT}/pm25_prediction.png")
print("saved pm25_prediction.png")