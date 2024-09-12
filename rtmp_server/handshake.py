# Dyrwolv Python rtmp server
# src/rtmp_server/handshake.py

import os
import struct
import time
import random
import logging
from ..utils.logger import log

RTMP_SIG_SIZE = 1536
VERSION = 0x03
BUFSIZE = 1537
RANDOM_SIZE = 1528

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%H:%M:%S'
)

''' Ok my issue all along was that i was thinking obs was going to do a simple handshake and
    not a complex one with hashes and security. so i guess now we will try to understand such things.
    maybe also shed a few tears.
'''


def DetectClientMessageFormat():
    # do magic
    pass


def create_s1():
    # do magic
    logging.info('Creating S1')
    zero_bytes = b'\x00\x00\x00\x00'
    randomBytes = os.urandom(RANDOM_SIZE)  # gonna need to document this
    s1_timestamp = int(time.time())
    handshakeBytes = struct.pack('>I', s1_timestamp) + zero_bytes + randomBytes
    logging.info(f'S1 random bytes: {handshakeBytes[:50]}.... length: {len(handshakeBytes)}')
    logging.info(f'S1 timestamp: {s1_timestamp}')
    return handshakeBytes


def create_s2(c1_data):
    log("Entered create_s2")
    client_time = struct.unpack('>I', c1_data[0:4])[0]  # unpack c1_data to get the client time
    client_random = c1_data[8:]  # unpack the c1_data to get the random bytes
    server_time = int(time.time())  # get our servers timestamp
    logging.info(f'Client time: {client_time}, client random: {client_random[:50]}.... server time: {server_time}')
    # Now if im understanding this correctly. S2 has | c1_time | s2_time | c1_random |
    s2 = struct.pack('>I', client_time) + struct.pack('>I', server_time) + client_random
    logging.info(f"Length of S2: {len(s2)}")
    return s2


def parse_c2(c2_data, s1_data, c1_data):
    logging.info("Entered parse_c2")
    c2_time = struct.unpack('>I', c2_data[0:4])[0]
    c2_time2 = struct.unpack('>I', c2_data[4:8])[0]
    c2_random = c2_data[8:8 + RANDOM_SIZE]
    ##########################################
    # unpack the other data... i feel like i could save cpu time by just saving it in the handle client..
    s1_time = struct.unpack('>I', s1_data[0:4])[0]
    c1_time = struct.unpack('>I', c1_data[0:4])[0]
    s1_random = s1_data[8:8 + RANDOM_SIZE]
    logging.info(f"c2_time: {c2_time} expected: {s1_time}")
    logging.info(f"c2_time2: {c2_time2} expected: {c1_time}")
    logging.info(f"c2_random: {c2_random.hex()[:50]}... expected: {s1_random.hex()[:50]}...")

    if s1_time != c2_time and c1_time != c2_time2 and c2_random != s1_random:
        logging.warning(f"contents of C2 is not what we expected")
        return False
    else:
        return True


# not sure why im going need this yet, but I'll add it
def CreateS0S1S2():
    # magic maybe?
    pass
