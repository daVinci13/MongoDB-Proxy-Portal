import os
import asyncio
from aiohttp import web
import motor.motor_asyncio

async def handle(request):
    # Get the MongoDB collection
    collection = request.app['db'].test_collection

    # Forward the request to the MongoDB server
    result = await collection.find_one()

    return web.json_response(result)

async def create_app(mongo_host, mongo_port):
    app = web.Application()
    
    # Set up MongoDB connection
    client = motor.motor_asyncio.AsyncIOMotorClient(f'mongodb://{mongo_host}:{mongo_port}')
    app['db'] = client.test

    # Add a route to handle incoming requests
    app.router.add_get('/', handle)

    return app

if __name__ == '__main__':
    mongo_host = os.getenv('mongoHost', 'localhost')
    mongo_port = int(os.getenv('mongoPort', 27017))

    app = asyncio.run(create_app(mongo_host, mongo_port))
    web.run_app(app, port=27000)
