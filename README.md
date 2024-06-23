# 🌐 MongoDB Proxy Portal

This script sets up a proxy portal that logs connections to a MongoDB database. It's designed to run in a Docker container and is configurable via environment variables.

## Description

The proxy server listens on the specified `PROXY_PORT` and forwards all connections to the MongoDB instance specified by `MONGO_HOST` and `MONGO_PORT`. It logs each connection's IP address and timestamp to the specified MongoDB database and collection.

## Environment Variables

- **`MONGO_USER`**: MongoDB username
- **`MONGO_PASS`**: MongoDB password
- **`MONGO_HOST`**: MongoDB host (default: `localhost`)
- **`MONGO_PORT`**: MongoDB port (default: `27017`)
- **`PROXY_PORT`**: Proxy port (default: `2222`)
- **`DB_NAME`**: Database name (default: `logs`)
- **`COLLECTION_NAME`**: Collection name (default: `connections`)

## Running with Docker

### Using Docker Run

```bash
docker run -d \
    -e MONGO_USER=your_mongo_user \
    -e MONGO_PASS=your_mongo_pass \
    -e MONGO_HOST=your_mongo_host \
    -e MONGO_PORT=27017 \
    -e PROXY_PORT=2222 \
    -e DB_NAME=logs \
    -e COLLECTION_NAME=connections \
    -p 2222:2222 \
    mongo-proxy-portal
```

### Using Docker Compose

Create a `docker-compose.yml` file with the following content:

```yaml
version: '3.8'

services:
  mongodb-proxy:
    image: mongo-proxy-portal
    environment:
      MONGO_USER: your_mongo_user
      MONGO_PASS: your_mongo_pass
      MONGO_HOST: your_mongo_host
      MONGO_PORT: 27017
      PROXY_PORT: 2222
      DB_NAME: logs
      COLLECTION_NAME: connections
    ports:
      - "2222:2222"
```

Then start the container with:

```bash
docker-compose up -d
```