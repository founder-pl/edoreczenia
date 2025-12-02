FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir requests webdavclient3

COPY sync_service.py .

CMD ["python", "sync_service.py"]
