#!/usr/bin/env python3
"""
OPTIONAL local stand-in for the Urban Observatory APIs and the dashboard.

This is not a brief requirement. Use it only if
http://smartcam.uo.ncl.ac.uk:8001 and
http://dashboard.cloud.ncl.ac.uk:8000 are unreachable.

It serves:
  GET  /sensor          JSON array of ~10 minutes of readings, looping every 9 minutes
  GET  /camera          a JPEG frame
  POST /api/records     multipart dashboard sink, saved under /app/output
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from flask import Flask, jsonify, request, send_file

HISTORY_PATH = os.getenv("HISTORY_PATH", "/app/pm25_history.json")
CAMERA_PATH = os.getenv("CAMERA_PATH", "/app/sample_frame.jpg")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/app/output")
WINDOW_SECONDS = 10 * 60
LOOP_SECONDS = 9 * 60

app = Flask(__name__)

with open(HISTORY_PATH, encoding="utf-8") as handle:
    HISTORY = json.load(handle)
HISTORY = sorted(HISTORY, key=lambda row: row["Timestamp"])
print(f"[mock] loaded {len(HISTORY)} PM2.5 readings")

# Readings are ~7.3 seconds apart in the official dump.
SPAN_MS = HISTORY[-1]["Timestamp"] - HISTORY[0]["Timestamp"]
print(f"[mock] history span {SPAN_MS} ms")


def window_for_now():
    elapsed = time.time() % LOOP_SECONDS
    # Slide a 10-minute window across the 8711-point series, looping every 9 minutes.
    start_index = int((elapsed / LOOP_SECONDS) * len(HISTORY)) % len(HISTORY)
    # Approximately 10 minutes of points (~82 at 7.3 s spacing).
    window_size = 82
    items = []
    for offset in range(window_size):
        item = HISTORY[(start_index + offset) % len(HISTORY)]
        items.append(
            {
                "Timestamp": item["Timestamp"],
                "Units": "ugm -3",
                "Variable": "PM2.5",
                "Sensor Name": "PER_AIRMON_MONITOR1135100",
                "Flagged as Suspect Reading": False,
                "Value": item["Value"],
            }
        )
    # Add a non-PM2.5 reading so the collector has to filter, as the brief describes.
    items.append(
        {
            "Timestamp": items[0]["Timestamp"],
            "Units": "ugm -3",
            "Variable": "NO2",
            "Sensor Name": "PER_AIRMON_MONITOR1135100",
            "Flagged as Suspect Reading": False,
            "Value": 6.2,
        }
    )
    return items


@app.get("/sensor")
def sensor():
    return jsonify(window_for_now())


@app.get("/camera")
def camera():
    return send_file(CAMERA_PATH, mimetype="image/jpeg")


@app.post("/api/records")
def create_record():
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    timestamp = request.form.get("timestamp")
    value = request.form.get("value")
    quality = request.form.get("predicted_quality")
    image = request.files.get("image")
    saved = None
    if image is not None:
        saved = os.path.join(
            OUTPUT_DIR, f"dashboard_{timestamp}_{int(time.time())}.jpg"
        )
        image.save(saved)
    record = {
        "timestamp": timestamp,
        "value": value,
        "predicted_quality": quality,
        "image": saved,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    log_path = os.path.join(OUTPUT_DIR, "dashboard_records.jsonl")
    with open(log_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
    print(f"[mock dashboard] stored {record}")
    return jsonify({"ok": True, "record": record}), 201


@app.get("/")
@app.get("/docs")
def docs():
    return (
        "<h1>Local mock Urban Observatory / dashboard</h1>"
        "<p>Optional only. Not required by the brief.</p>"
        "<ul>"
        "<li>GET /sensor</li>"
        "<li>GET /camera</li>"
        "<li>POST /api/records (multipart: timestamp, value, predicted_quality, image)</li>"
        "</ul>"
    )


if __name__ == "__main__":
    # :8001 for UO-style paths, and a second WSGI server is awkward, so we
    # bind 8001 and also serve /api/records here. docker-compose maps 8000
    # and 8001 onto this one process via a tiny sidecar in the Dockerfile.
    app.run(host="0.0.0.0", port=8001, debug=False)
