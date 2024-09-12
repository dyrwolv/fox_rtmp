# Dyrwolv Python rtmp server
# src/rtmp_server/server.py

import asyncio
import logging
# import time
import uuid

from src.rtmp_server import handshake

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%H:%M:%S'
)

RTMP_VERSION = b'\x03'

# a dictionary to store our live users
LiveUsers = {}


class Client:
    """
    A class that represents a client.

    This class keeps track of the client's id and IP address.

    Attributes:
        id (str): The unique identifier of the client.
        ip_addr (str): The IP address of the client.
    """

    def __init__(self):
        self.id = str(uuid.uuid4())
        self.ip_addr = '0.0.0.0'  # placeholder ip address
        self.reader = None
        self.writer = None


class FoxRtmp:
    """FoxRtmp constructor."""

    def __init__(self, host, port):
        # Server properties...
        self.host = host
        self.port = port
        self.logger = logging.getLogger('RTMPServer')
        self.logger.setLevel(logging.INFO)
        self.client_info = {}

    ''' Ok now we're going to attempt to handle a client connection.
        we want to store the client ip address into a Client class giving it a unique id
        so that we can then reference it later from the LiveUsers
    '''

    async def handle_client(self, reader, writer):
        """
        Handle a client connection.
        reader: The StreamReader object to read data from the client.
        writer: The StreamWriter object to write data to the client.
        """
        user = Client()  # makes user a Client() Object
        # I think we need to set up input and output now for our user.
        user.reader = reader  # set up to read incoming data from the user
        user.writer = writer  # set up to send data to the user
        self.client_info[user.id] = user  # Create an id for our user and store it as a key
        ####################################################################################
        # now we want to store the ip address of the user and log a message about whose connected
        self.client_info[user.id].ip_addr = writer.get_extra_info('peername')  # 'peername' gives the remote address
        # to which the socket is connected, result of socket.socket.getpeername() (None on error)
        self.logger.info("Client connected from %s", self.client_info[user.id].ip_addr)

        ''' ok now we're back to the handshake process which i couldn't figure out before.
        hopefully this time it'll go better
        '''
        try:
            # result =
            # enter handshake with the user, with a timeout of 5 seconds?
            await asyncio.wait_for(self.perform_handshake(user.id), timeout=5)
        except asyncio.TimeoutError:
            self.logger.error("Handshake timed out. Closing connection: %s", self.client_info[user.id].ip_addr)
            await self.disconnect(user.id)
            return

    async def perform_handshake(self, user_id):
        user = self.client_info[user_id]
        # time to actually perform the damn handshake. maybe we can get some progress...
        # im also not sure if I should be storing this stuff in here?
        c0_data = await user.reader.readexactly(1)  # read exactly 1 byte from the user to get the RTMP VER#

        if c0_data != RTMP_VERSION:  # handle if the RTMP VER is different then what we are expecting
            await self.disconnect(user.id)
            self.logger.info(f"Invalid C0 data {c0_data}, client disconnected: %s", user.ip_addr)
            return

        # Let's get the C1 data from the user
        c1_data = await user.reader.readexactly(1536)  # grabs the next 1536 bytes containing C1
        # There's probably some weird stuff I need to do to handle secure connections at this point
        # i should send S0 at this point I think
        s1_data = handshake.create_s1()
        s2_data = handshake.create_s2(c1_data) # giving it the c1_data, but it will need to be unpacked
        data = b'\x03' + s1_data + s2_data
        user.writer.write(data)
        c2_data = await user.reader.readexactly(1536)
        if handshake.parse_c2(c2_data, s1_data, c1_data):
            self.logger.info("Handshake successful")
        else:
            self.logger.error("Handshake failed. Closing connection: %s", self.client_info[user.id].ip_addr)
            await self.disconnect(user.id)

    async def disconnect(self, user_id):
        user = self.client_info[user_id]
        # add some logic later to detect if the user is streaming, or if they are a viewer
        # I think I may also want to clear their packet buffer? user.['IncomingPackets'].clear()

        # remove the user from our dictionary.
        del self.client_info[user_id]
        try:
            user.writer.close()  # close the connection
            await user.writer.wait_closed()  # waits for it to close?
            self.logger.info("%s disconnected", user.ip_addr)
        except Exception as e:
            # Handle the exception here, perform other tasks, log the error.
            self.logger.error(f"Error occurred while disconnecting the client: {user.ip_addr} with the error {e}")

    async def start_server(self):
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


def rtmp(host, port):
    server = FoxRtmp(host, port)
    asyncio.run(server.start_server())

