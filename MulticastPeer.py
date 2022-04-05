import asyncio
import socket
import struct
from time import time

from async_generator import yield_

class MulticastPeer():
    """
    Multicast Peer
    ----------------
    Communication protocol
    
    Every package sent must be formated as follows:
            [ID] [TIME] [STATUS]
    """
    def __init__(self, id, pipe_end=None, group:str='228.5.6.7', port:int=6789):
        self.group = group
        self.port = port
        self.state = 'RELEASED'
        self.queue = []
        self.group_members = []
        self.id = str(id)
        self.count_responses = 0
        self.pipe_end = pipe_end

    def request_lock(self):
        self.state = 'WANTED'
        self.request_time = time()

        self.send('{0} {1} {2}'.format( \
            self.id, self.request_time, \
                self.state).encode())

        if self.count_responses == len(self.group_members):
            self.state = 'HELD'

    def release_lock(self):
        pass

    async def join(self, number_of_tries=3):
        for i in range(number_of_tries):
            await asyncio.sleep(0.1)

            await self.send('{0} {1} {2}'.format( \
                self.id, time(), 'JOIN').encode())

    async def send(self, message:bytes, verbose_flag:bool=True):
        """
        Communication protocol

        Every package sent must be formated as follows:
            [ID] [TIME] [STATUS]   
        """
        multicast_group = (self.group, self.port)

        # Create the datagram socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Set a timeout so the socket does not block
        # indefinitely when trying to receive data.
        sock.settimeout(60)

        # Set the time-to-live for messages to 1 so they do not
        # go past the local network segment.
        ttl = struct.pack('b', 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

        try:
            # Send data to the multicast group
            sent = sock.sendto(message, multicast_group)

            # Look for responses from all recipients
            while True:
                try:
                    data, server = sock.recvfrom(4096)
                    received_message = data.decode().split(' ')

                    res = {}

                    res['id'] = received_message[0]
                    res['time'] = received_message[1]
                    res['status'] = received_message[2]
                    res['address'] = server

                except socket.timeout:
                    if verbose_flag:
                        print('\nPeer [{0}]:'.format(self.id), end=' ')
                        print('no more responses, socket timeout.')

                    break
                else:
                    if verbose_flag:
                        print('\nPeer [{0}]:'.format(self.id), end=' ')
                        print('received {!r} from {}\n'.format(
                            data, server))

                    self.count_responses += 1

                    if self.count_responses >= len(self.group_members):
                        self.count_responses = 0
                        return 0
                
                await asyncio.sleep(0.1)
        finally:
            sock.close()

        return 1

        
    def listen(self, pipe_end=None, verbose_flag:bool=True):
        """
        Communication protocol
        
        Every package sent must be formated as follows:
            [ID] [TIME] [STATUS]   
        """
        multicast_group = self.group
        server_address = (self.group, self.port)

        # Create the socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

        # Bind to the server address
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(server_address)

        # Tell the operating system to add the socket to
        # the multicast group on all interfaces.
        group = socket.inet_aton(multicast_group)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        sock.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_ADD_MEMBERSHIP,
            mreq)

        # Receive/respond loop
        while True:
            print('Receiving...')
            try:
                data, address = sock.recvfrom(4096)
                received_message = data.decode().split(' ')

                newmsg = {}

                newmsg['id'] = received_message[0]
                newmsg['time'] = received_message[1]
                newmsg['status'] = received_message[2]
                newmsg['address'] = address

                if newmsg['status'] == 'WANTED':
                    if verbose_flag:
                        print('\nPeer [{0}]:'.format(self.id), end=' ')
                        print(address,'({0}) wants the resource'.format(newmsg['id']))

                    if self.state == 'HELD' or \
                        (self.state == 'WANTED' and self.request_time < newmsg['time']):
                        self.queue.append(newmsg)
                    else:
                        sock.sendto(\
                            '{0} {1} {2}'.format(self.id, time(), self.state),\
                            address)

                elif newmsg['status'] == 'JOIN' and \
                    newmsg['id'] != self.id and \
                    newmsg['id'] not in self.group_members:

                    self.group_members.append(newmsg['id'])
                    
                    if verbose_flag:
                        print('\nPeer [{0}]:'.format(self.id), end=' ')
                        print(address,'({0}) joined the group'.format(newmsg['id']))

                else:
                    if verbose_flag:                        
                        print('\nPeer [{0}]:'.format(self.id), end=' ')
                        print('received {} bytes from {}'.format(
                        len(data), address))
                        print(data)

                    sock.sendto('{0} {1} {2}'.format(self.id, time(), 'ACK')\
                        .encode(), address)

                    
            except Exception:
                raise Exception