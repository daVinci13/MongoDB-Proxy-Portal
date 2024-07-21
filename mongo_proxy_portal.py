import os
import asyncio
import logging
from aiohttp import web
import motor.motor_asyncio
from datetime import datetime
from asyncio import StreamReader, StreamWriter

db_name = os.getenv('DB_NAME', 'logs')
collection_name = os.getenv('COLLECTION_NAME', 'connections')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def ensure_collection(db):
    collections = await db.list_collection_names()
    if collection_name not in collections:
        await db.create_collection(collection_name)
    await db[collection_name].create_index("ip", unique=True)

async def log_connection(client, ip):
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

async def handle_client(client_reader: StreamReader, client_writer: StreamWriter, mongo_host, mongo_port, mongo_client):
    peername = client_writer.get_extra_info('peername')
    if peername:
        ip = peername[0]
        await log_connection(mongo_client, ip)

    try:
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

async def create_app(mongo_host, mongo_port):
    app = web.Application()

    # Set up MongoDB connection
    client = motor.motor_asyncio.AsyncIOMotorClient(f'mongodb://{mongo_host}:{mongo_port}')
    app['db'] = client.test
    await ensure_collection(client.test)

    return app

async def tcp_server(mongo_host, mongo_port, mongo_client):
    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, mongo_host, mongo_port, mongo_client),
        '0.0.0.0', 27000
    )

    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    mongo_host = os.getenv('mongoHost', 'localhost')
    mongo_port = int(os.getenv('mongoPort', 27017))

    loop = asyncio.get_event_loop()

    # Set up MongoDB connection
    mongo_client = motor.motor_asyncio.AsyncIOMotorClient(f'mongodb://{mongo_host}:{mongo_port}')

    app = loop.run_until_complete(create_app(mongo_host, mongo_port))

    # Start HTTP server
    web_task = loop.create_task(web._run_app(app, port=27000))

    # Start TCP proxy server
    tcp_task = loop.create_task(tcp_server(mongo_host, mongo_port, mongo_client))

    try:
        loop.run_until_complete(asyncio.gather(web_task, tcp_task))
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()



