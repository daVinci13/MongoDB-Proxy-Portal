import os
import asyncio
from asyncio import StreamReader, StreamWriter

async def forward_data(reader: StreamReader, writer: StreamWriter):
    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except Exception as e:
        print(f"Error while forwarding data: {e}")
    finally:
        writer.close()
        await writer.wait_closed()

async def handle_client(client_reader: StreamReader, client_writer: StreamWriter, mongo_host, mongo_port):
    peername = client_writer.get_extra_info('peername')
    print(f"Connection from {peername}")

    try:
        mongo_reader, mongo_writer = await asyncio.open_connection(mongo_host, mongo_port)
        print(f"Connected to MongoDB at {mongo_host}:{mongo_port}")

        forward_client_to_mongo = forward_data(client_reader, mongo_writer)
        forward_mongo_to_client = forward_data(mongo_reader, client_writer)

        await asyncio.gather(forward_client_to_mongo, forward_mongo_to_client)
    except Exception as e:
        print(f"Error handling client {peername}: {e}")
        import traceback
        print("".join(traceback.format_exception(None, e, e.__traceback__)))
    finally:
        client_writer.close()
        await client_writer.wait_closed()
        print(f"Connection from {peername} closed")

async def tcp_server(mongo_host, mongo_port):
    server = await asyncio.start_server(
        lambda r, w: handle_client(r, w, mongo_host, mongo_port),
        '0.0.0.0', 27017
    )

    async with server:
        print(f"Proxy server listening on port 27017, forwarding to {mongo_host}:{mongo_port}")
        await server.serve_forever()

if __name__ == '__main__':
    mongo_host = os.getenv('mongoHost', 'localhost')
    mongo_port = int(os.getenv('mongoPort', 27017))

    loop = asyncio.get_event_loop()

    # Start TCP proxy server
    try:
        loop.run_until_complete(tcp_server(mongo_host, mongo_port))
    except KeyboardInterrupt:
        print("Server interrupted by user")
    finally:
        loop.close()
        print("Event loop closed")
