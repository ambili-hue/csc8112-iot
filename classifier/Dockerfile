FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY classifier.py model.tflite scaler.json ./
CMD ["python", "-u", "classifier.py"]