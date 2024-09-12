# Dyrwolv Python rtmp server
# src/rtmp_server/old_rtmp.py

import asyncio
import logging
import time
from src.rtmp_server import handshake
import uuid  # not sure yet

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%H:%M:%S'
)

RTMP_VERSION = b'0x03'

# dict to store live users
LiveUsers = {}
# dict to sore clients?
PlayerUsers = {}


class Client:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.client_ip = '0.0.0.0'

        # put more stuff here as needed?
        self.Time0 = time.time()
        self.Streams = 0
        self.IncomingPackets = {}  # might be helpful
        self.Players = {}  # connected viewers


class RTMPServer:
    def __init__(self, host, port):
        # sock
        # server properties
        self.host = host
        self.port = port
        self.logger = logging.getLogger('RTMPServer')
        self.logger.setLevel(logging.INFO)
        self.client_info = {}

    async def handle_client(self, reader, writer):
        # create a new client state for each connected client
        new_client = Client()
        self.client_info[new_client.id] = new_client
        self.client_info[new_client.id].clientID = new_client.id

        # these are probably for the asyncio
        self.client_info[new_client.id].reader = reader
        self.client_info[new_client.id].writer = writer
        ####################################################

        # store the ip address and log a message about who connected
        self.client_info[new_client.id].ip_addr = writer.get_extra_info('peername')
        self.logger.info("New client connected: %s", self.client_info[new_client.id].ip_addr)

        ''' ok now we're back to the handshake process which i couldnt figure out before.
        hopefully this time it'll go better
        '''
        # let's try to perform a handshake
        try:
            # wait for handshake with the client? timeout after 5 seconds?
            await asyncio.wait_for(self.perform_handshake(new_client.id), timeout=5)
        except asyncio.TimeoutError:
            self.logger.error("Handshake timeout. Closing connection: %s",
                              self.client_info[new_client.id].ip_addr)
            await self.disconnect(new_client.id)
            return

    async def disconnect(self, client_id):
        # close the client connection
        client_state = self.client_info[client_id]
        if client_state.stream_mode == 'live':
            # disconnect players?
            print("disconnect everyone?")

        client_state['IncomingPackets'].clear()
        del self.client_info[client_id]
        try:
            client_state.writer.close()
            await client_state.writer.wait_closed()
            self.logger.info("Client disconnected: %s", client_state.ip_addr)
        except Exception as e:
            # Handle the exception here, perform other tasks, or log the error.
            self.logger.error(f"Error occurred while disconnecting client: {e}")

    async def perform_handshake(self, client_id):
        # Perform the RTMP handshake with the client
        client_state = self.client_info[client_id]
        c0_data = await client_state.reader.readexactly(1)  # get the first byte containing c0
        if c0_data != RTMP_VERSION:
            client_state.writer.close()
            await client_state.writer.wait_closed()
            self.logger.info(f"Invalid C0 data {c0_data}, client disconnected: %s", client_state.ip_addr)

        c1_data = await client_state.readexactly(1536)  # get the next 1536 bytes containing C1
        clientType = bytes([3])  # not sure what this is yet
        # sure yet probably related to secure connections
        # messageFormat = handshake.detectClientMessageFormat(c1_data)
        s1_data = handshake.CreateS1()
        s2_data = handshake.CreateS2(c1_data)
        data = s1_data + s2_data
        client_state.writer.write(data)
        s1_data = await client_state.reader.readexactly(len(s1_data))

        self.logger.debug("Handshake Done!")

    async def start_server(self, client_id):
        server = await asyncio.start_server(self.handle_client, self.host, self.port)

        addr = server.sockets[0].getsockname()
        self.logger.info("RTMP server started on %s", addr)

        try:
            async with server:
                await server.serve_forever()
        except KeyboardInterrupt:
            exit(0)
        finally:
            server.close()
            self.logger.info("RTMP server stopped")


def RTMP(host, port):
    rtmp_server = RTMPServer(host, port)
    asyncio.run(rtmp_server.start_server("server"))


class RTMPServerProtocol(asyncio.Protocol):
    def __init__(self):
        self.state = 'handshake'
        self.buffer = b''
        self.transport = None
        self.handshake = handshake.RTMPHandshake()
        self.peername = None
        logging.info(f"Initialized with state: {self.state}")

    def connection_made(self, transport):
        self.transport = transport
        self.peername = transport.get_extra_info('peername')
        logging.info(f"Connection made with {self.peername[0]}:{self.peername[1]}")

    async def data_received(self, data):
        self.buffer += data
        logging.info(f"Data received in state {self.state}: {len(data)} bytes")
        logging.info(f"Buffer now has {len(self.buffer)} bytes")
        if self.state == 'handshake':
            handshake.handle_handshake(self)
        if self.state == 'post_handshake':
            handshake.handle_post_handshake(self)
        elif self.state == 'streaming':
            self.handle_stream()

    async def perform_handshake(self):
        # Perform the RTMP handshake with the client
        c0_data = await self.get  # get the first byte containing c0

        c1_data = await client_state.readexactly(1536)  # get the next 1536 bytes containing C1
        clientType = bytes([3])  # not sure what this is yet
        # sure yet probably related to secure connections
        # messageFormat = handshake.detectClientMessageFormat(c1_data)
        s1_data = handshake.CreateS1()
        s2_data = handshake.CreateS2(c1_data)
        data = s1_data + s2_data
        client_state.writer.write(data)
        s1_data = await client_state.reader.readexactly(len(s1_data))

    def handle_stream(self):
        pass


def run_server(ip_address, port):
    logging.info("Starting RTMP server...")
    loop = asyncio.new_event_loop()
    coro = loop.create_server(RTMPServerProtocol, ip_address, port)
    server = loop.run_until_complete(coro)
    logging.info(f"RTMP server started on {ip_address}:{port}")
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.close()
        loop.run_until_complete(server.wait_closed())
        loop.close()
        logging.info("RTMP server has stopped")
