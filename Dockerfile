FROM python:3.10-alpine3.20
WORKDIR /app
RUN apk add --no-cache gcc musl-dev libffi-dev python3-dev
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python3", "mongo_proxy_portal.py"]

