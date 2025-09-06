FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt /app/
RUN pip3 install --no-cache-dir -r requirements.txt
RUN pip install clickhouse-connect
COPY processor /app/processor
COPY tests /app/tests
EXPOSE 9000
CMD ["python", "-m", "processor.processor"]
