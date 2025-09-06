FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt /app/
RUN pip3 install --no-cache-dir -r requirements.txt
COPY collectors /app/collectors
EXPOSE 9100
CMD ["python", "-m", "collectors.usgs_quakes"]
