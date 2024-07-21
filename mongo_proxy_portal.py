import asyncio

async def handle_client(reader, writer):
    addr = writer.get_extra_info('peername')
    print(f"Connected to {addr}")

    while True:
        data = await reader.read(100)  # Adjust the number of bytes to read as needed
        if not data:
            print("Connection closed by the client")
            break

        message = data.decode()
        print(f"Received: {message}")

    writer.close()
    await writer.wait_closed()

async def main():
    server = await asyncio.start_server(
        handle_client, '0.0.0.0', 27017
    )

    addr = server.sockets[0].getsockname()
    print(f"Serving on {addr}")

    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    asyncio.run(main())
