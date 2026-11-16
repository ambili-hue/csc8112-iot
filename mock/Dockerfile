FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY mock_server.py start.sh sample_frame.jpg ./
# pm25_history.json is bind-mounted in compose, but copy if present.
COPY pm25_history.json ./
EXPOSE 8000 8001
CMD ["sh", "start.sh"]
