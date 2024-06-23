import asyncio
import logging
import os
import motor.motor_asyncio
from asyncio import StreamReader, StreamWriter
from datetime import datetime
from urllib.parse import urlparse

mongo_host = os.getenv('MONGO_HOST', 'localhost')
mongo_port = int(os.getenv('MONGO_PORT', 27017))
proxy_port = int(os.getenv('PROXY_PORT', 2222))

client = None

db_name = os.getenv('DB_NAME', 'logs')
collection_name = os.getenv('COLLECTION_NAME', 'connections')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def ensure_collection():
    db = client[db_name]
    collections = await db.list_collection_names()
    if collection_name not in collections:
        await db.create_collection(collection_name)
    await db[collection_name].create_index("ip", unique=True)

async def log_connection(ip):
    db = client[db_name]
    collection = db[collection_name]
    try:
        document = await collection.find_one({"ip": ip})
        if document:
            await collection.update_one(
                {"ip": ip},
                {"$inc": {"count": 1}, "$set": {"last_seen": datetime.utcnow()}}
            )
        else:
            await collection.insert_one(
                {"ip": ip, "count": 1, "first_seen": datetime.utcnow(), "last_seen": datetime.utcnow()}
            )
    except Exception as e:
        logger.error(f"Error logging connection: {e}")

async def forward_data(reader: StreamReader, writer: StreamWriter):
    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except ConnectionResetError as e:
        logger.error(f"Connection reset during data forwarding: {e}")
    except (asyncio.CancelledError, OSError) as e:
        logger.error(f"Error during data forwarding: {e}")
    finally:
        writer.close()
        await writer.wait_closed()

async def handle_client(client_reader: StreamReader, client_writer: StreamWriter):
    global client
    peername = client_writer.get_extra_info('peername')
    if peername:
        ip = peername[0]
        await log_connection(ip)

    try:
        uri_data = await client_reader.read(4096)
        uri = uri_data.decode().strip()
        parsed_uri = urlparse(uri)
        mongo_user = parsed_uri.username
        mongo_pass = parsed_uri.password

        client = motor.motor_asyncio.AsyncIOMotorClient(uri, maxPoolSize=100)
        await ensure_collection()
        
        mongo_reader, mongo_writer = await asyncio.open_connection(mongo_host, mongo_port)
        forward_client_to_mongo = forward_data(client_reader, mongo_writer)
        forward_mongo_to_client = forward_data(mongo_reader, client_writer)
        await asyncio.gather(forward_client_to_mongo, forward_mongo_to_client)
    except ConnectionResetError as e:
        logger.error(f"Connection reset by peer: {e}")
    except Exception as e:
        logger.error(f"Error handling client: {e}")
    finally:
        client_writer.close()
        await client_writer.wait_closed()

async def cleanup_inactive_connections(timeout):
    while True:
        await asyncio.sleep(timeout)
        now = datetime.utcnow().timestamp()
        for task in asyncio.all_tasks():
            if task.done():
                continue
            last_activity = task.get_last_activity_time()
            if now - last_activity > timeout:
                task.cancel()

async def main():
    server = await asyncio.start_server(handle_client, "0.0.0.0", proxy_port)
    logger.info(f"Server listening on port {proxy_port}")
    cleanup_task = asyncio.create_task(cleanup_inactive_connections(300))
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
