# Dyrwolv Python rtmp server
# src/rtmp_server/old_rtmp.py

# ok i think im messing it up, by not sending messaging in the right order

import asyncio
import struct
import time
import os
import old_rtmp.handshake as handshake
# not sure why i need these yet, but im sure ill find out


#... need to remember how classes and class inheritance works...
HANDSHAKE = 'handshake'
POST_HANDSHAKE = 'post_handshake'
STREAMING = 'streaming'
WAITING_FOR_DATA = 'waiting'
PACKET_SIZE = 1537  # 1 byte for version + 1536 bytes for C1
RANDOM_SIZE = 1528  # Adjusted to match typical RTMP random size (1528 bytes)


#should maybe figure out how to move these into the class

def log(message):
    # logging function to print messages with a timestamp.
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}")
    
class RTMPServerProtocol(asyncio.Protocol):
# this means RTMPServerProtocol now has the same functionality as asyncio.protocol, if i am reading it correctly
#asyncio.protocol is an interface for me to do bidirectional transport, over say a tcp connection

    def __init__(self):
        #sets the state of the protocol to handshake
        self.state = HANDSHAKE
        # set up a buffer with an empty bytes object
        self.buffer = b''
        self.s1_time = None
        self.c1_time = None
        self.s1_random = None
        self.c1_random = None
        
        log(f"Initialized with state: {self.state}")

    
    def connection_made(self, transport):
        # not sure yet.... 
        self.transport = transport
        log("Connection made")
        
    def data_received(self, data):
        #store recieved data into our buffer
        self.buffer += data
        log(f"Data received in state {self.state}: {len(data)} bytes")
        log(f"Buffer now has {len(self.buffer)} bytes")
        
        #check what state we're in
        if self.state == POST_HANDSHAKE: # checks if we're in a handshake 
            self.handle_post_handshake()
        if self.state == HANDSHAKE:
            self.handle_handshake()
        # not sure if i need to handle the post_handshake in here too since im going into it directly from handle_handshake
        if self.state == STREAMING: # placeholder for a non handshake state
            self.handle_stream()
        # handle other states ( 'streaming' etc) here
        
    def handle_client(self, client_socket):
        pass
    def handle_handshake(self):
        #start rtmp handshake
        #im probably forgetting some logic to wait on the client
        log("entered into handshake")
        if len(self.buffer) < PACKET_SIZE:
            log("Not enough data to establish a handshake....")
            return # not enough data for a handshake...
        
        '''client -> server handshake C0 + C1
        extract the first byte containing the RTMP Version     
        extract the remaining bytes starting at index 1 ending at 1537 C1 now contains
        The time, zero field, and random data
        '''
        c0 = self.buffer[0:1]
        c1 = self.buffer[1:PACKET_SIZE]
        self.buffer = self.buffer[PACKET_SIZE:] # clear the bufffer
        
        log("Received C0 and C1")
        log(f"C0: {c0.hex()}")
        log(f"C1: {c1.hex()[:50]}...") # only first 50 chars for brevity
        
        # check C0
        if c0 != b'\x03':
            # if C0 is not 0x03 close the connection
            log("Invalid RTMP version. Closing connection")
            self.transport.close()
            return
        
        # ok now we need to process the data
        # parse C1
        #used gpt to help with this, but im now gonna go look at what its doing
        #sidenote, probably horrible that im doing this on my oled monitor... OH WELL
        
        ''' how struct.unpack() is working
        struct.unpack(format, buffer)
        
        struct.unpack('>I', c1[0:4])[0]
                    >I the format?
                    > = big endian
                    I means it's an unsigned int standard size 4
                    c1[0:4] is our buffer
        result is a tuple even if it contrains 1 item. buffer size in bytes must match the size required by the format
        as reflected by calcsize(). <- gonna test and play with this later.
        if first character is not definined in the src/docs/struct_unpack_formatting.png '@'(native) is assumed
        
        we're unpacking bytes 0 - 4 and returning an unsigned int(typically 4 bytes)
        and then taking index 0 of the tuple?
        index 0 of the tuple is the first and should be the only item in it
        '''
        self.c1_time = struct.unpack('>I', c1[0:4])[0] # we figured it out with the comment block above
        c1_zero = struct.unpack('>I', c1[4:8])[0] # this will take the next 4 bytes and return an unsigned int
        self.c1_random = c1[8:]  # assigns the pseudo-random data
        
        log(f"C1 Time: {self.c1_time}, C1 Zero: {c1_zero}")
        log(f"C1 Random: {self.c1_random.hex()[:50]}...")
        log(f"size of C1 Random: {len(self.c1_random)}")
        
        
        '''visual representation so far
        | C0 (1 byte) | C1 (1536 bytes) | remaining data (presumed empty) |
        '''
        # should probably test this?
        
        # C0 and C1 have been recieved and processed
        
        # we should now send S0 + S1
        
        '''Server -> Client: S0 + S1
            set our version number 0x03
            get current time(epoch time?)
            pack the data up with struct.pack('>I', data)
            send it off with a transport.write
        '''
        s0 = b'\x03'
        self.s1_time = int(time.time())
        self.s1_random = os.urandom(RANDOM_SIZE)
        log(f"size of S1 Random: {len(self.s1_random)}")
        s1 = struct.pack('>I', self.s1_time) + struct.pack('>I', c1[4:8][0]) + self.s1_random
        # S1 should now be | S1_time | Zero 0 | Random bytes(RANDOM_SIZE) |
        #pack it up and send it off
        # sends our s0 + s1 response to the client
        self.transport.write(s0 + s1) 
        
        log(f"Sent S0: {s0.hex()} and S1 Time: {self.s1_time}")
        
        #im gonna assume chatgpts explanation of whats in s2 is correct
        # now we have to send off a s2 response. 
        s2 = struct.pack('>I', self.c1_time) + struct.pack('>I', self.s1_time) + self.c1_random
        self.transport.write(s2)
        log(f"Sent S2 Time: {self.c1_time}, S2 Time2: {self.s1_time}")
        log(f"Size of S2 Echo: {len(self.c1_random)}")
        
        # our handshake should, in theory be complete now. i could probably check C2, which is smart
        # checking c2...
        #store data for post handshake processing
        #self.s1_time = s1_time
        #self.c1_time = c1_time
        #self.s1_random = s1_random
        
        self.state = POST_HANDSHAKE
        log(f"State changed to: {self.state}")
        
        
        
    def handle_post_handshake(self):
        log("Entered post_handshake")
        if len(self.buffer) < PACKET_SIZE:
            log("Not enough data for C2...")
            return

        c2 = self.buffer[:PACKET_SIZE]
        self.buffer = self.buffer[PACKET_SIZE:]

        c2_time = struct.unpack('>I', c2[0:4])[0]
        c2_time2 = struct.unpack('>I', c2[4:8])[0]  # Correct extraction
        c2_echo = c2[8:8 + RANDOM_SIZE]
        
        log(f"C2 Time: {c2_time}, C2 Time2: {c2_time2}")
        log(f"C2 Echo: {c2_echo.hex()[:50]}...")

        # Check if the sizes match
        if len(c2_echo) != len(self.s1_random):
            log(f"Size mismatch: C2 Echo size {len(c2_echo)} vs S1 Random size {len(self.s1_random)}")
            return

        # Compare bytes directly to identify discrepancies
        match = self.s1_time == c2_time and self.s1_random == c2_echo
        if match:
            log("RTMP handshake completed correctly")
            log(f"Expected S1 Time: {self.s1_time}, C1 Time: {self.c1_time},  S1 Random: {self.s1_random.hex()[:50]}...")
            log(f"Received C2: C2_time={c2_time}, C2_time2={c2_time2}, C2_Echo={c2_echo.hex()[:50]}...")
            log("Ready for further RTMP commands")
            self.state = STREAMING
            log(f"State changed to: {self.state}")
        else:
            log(f"Received C2: C2_time={c2_time}, C2_time2={c2_time2}, C2_Echo={c2_echo.hex()[:50]}...")
            log(f"Expected S1 Time: {self.s1_time}, C1 Time: {self.c1_time},  S1 Random: {self.s1_random.hex()[:50]}...")
            log(f"Size of S1_random: {len(self.s1_random)}, Size of C2 Echo: {len(c2_echo)}")
            
    
    
    def handle_stream(self):
        log("we've entered the stream")
        
        

def run_server():
    IP_ADDRESS = '0.0.0.0'
    PORT = 1935
    
    log("Starting RTMP server...")
    #add in RTMP server code here
    
    ''' asyncio stuff... need to read
    
    asyncio.get_event_loop()
    gets the current event loop. not sure what that means
    
    we do need to create the server though
    oh boy.. the docs for this one loop.create_server()
    what is a coroutine?
    '''
    loop = asyncio.new_event_loop()
    coro = loop.create_server(RTMPServerProtocol,IP_ADDRESS, PORT) # create the server with our ip address and port of choice
    server = loop.run_until_complete(coro) # runs the coroutine until it completes run_until_complete returns the server object once it finishes
    
    log(f"RTMP server started on {IP_ADDRESS}:{PORT}")
    
    #try running the server, but exit upon a keyboard intterupt signal
    try: 
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.close()
        loop.run_until_complete(server.wait_closed())
        loop.close()
        log("RTMP server stopped")

if __name__ == '__main__':
    run_server()
