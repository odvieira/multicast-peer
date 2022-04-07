import asyncio
import multiprocessing
import select
import socket
import struct
import sys
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

    def __init__(self, id, pipe_end: multiprocessing.Pipe = None,
                 group: str = '228.5.6.7', port: int = 6789):
        self.group = group
        self.port = port
        self.state = 'RELEASED'
        self.queue = []
        self.group_members = []
        self.id = str(id)
        self.responses_to_rlock = []
        self.pipe_end = pipe_end
        self.request_time = -1.0
        self.inputs = []
        self.outputs = []
        self.exit = False

        self.multicast_group = (self.group, self.port)

        # Lock requester
        self.create_lock_sock()

        # Listener
        self.create_listener()

        # Create the datagram socket
        self.join_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # The socket does not block
        # indefinitely when trying to receive data.
        self.join_sock.setblocking(0)

        # Set the time-to-live for messages to 1 so they do not
        # go past the local network segment.
        ttl = struct.pack('b', 1)
        self.join_sock.setsockopt(
            socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

        return

    def close(self):
        self.listener_socket.close()
        self.join_sock.close()
        self.lock_sock.close()
        return

    def create_lock_sock(self):
        # Create the datagram socket
        self.lock_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # The socket does not block
        # indefinitely when trying to receive data.
        self.lock_sock.setblocking(0)

        # Set the time-to-live for messages to 1 so they do not
        # go past the local network segment.
        ttl = struct.pack('b', 1)
        self.lock_sock.setsockopt(
            socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

    def create_listener(self) -> int:
        multicast_group = self.group
        server_address = (self.group, self.port)

        # Create the socket
        sock = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

        # Non blocking socket
        sock.setblocking(0)

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

        self.listener_socket = sock

        self.inputs.append(self.listener_socket)

        return 0

    async def join(self):
        # Send data to the multicast group
        sent = self.join_sock.sendto(
            '{0} {1} {2}'.format(
                self.id, time(), 'JOIN').encode(), self.multicast_group)

        # Sockets from which we expect to read
        self.inputs.append(self.join_sock)

    async def active(self):
        while True:
            if self.pipe_end.poll():
                try:
                    command_received = self.pipe_end.recv()
                except EOFError:
                    self.pipe_end.close()
                    raise
                except:
                    raise
                else:
                    if command_received == 'JOIN':
                        await self.join()
                    elif command_received == 'RLOCK':
                        await self.request_lock()
                    elif command_received == 'EXIT':
                        self.close()
                        self.exit = True
                        return
            else:
                await asyncio.sleep(0.1)

    def release_lock(self):
        pass

    async def request_lock(self, verbose_flag: bool = True) -> None:
        """
        Args:
                        verbose_flag (bool, optional): Print to the output internal
                                                        states. Defaults to True.
        """

        self.state = 'WANTED'
        self.request_time = time()

        msg = '{0} {1} {2}'.format(
            self.id, self.request_time,
            self.state).encode()

        try:
            # Send data to the multicast group
            sent = self.lock_sock.sendto(msg, self.multicast_group)
        except:
            raise
        else:
            self.inputs.append(self.lock_sock)

    async def listen(self, verbose_flag: bool = True) -> None:
        """
        Args:
                        verbose_flag (bool, optional): Prints internal state.
                        Defaults to True.

        Every package are formated as follows:
                        [ID] [TIME] [STATUS]
        """

        while True:
            # Wait for at least one of the sockets to be
            # ready for processing
            if self.exit:
                return

            if not len(self.inputs) > 0:
                await asyncio.sleep(0.01)

            try:
                readable, writable, exceptional = select.select(
                    self.inputs, self.outputs, self.inputs, 0)
            except:
                raise

            if not len(readable) > 0:
                await asyncio.sleep(0.01)

            for s in readable:
                try:
                    data, address = s.recvfrom(4096)
                except:
                    raise
                else:
                    if verbose_flag:
                        print('\nPeer [{0}]:'.format(self.id), end=' ')
                        print('received {} bytes from {}'.format(
                            len(data), address))
                        print(data)

                    received_message = data.decode().split(' ')

                    res = {}

                    res['id'] = received_message[0]
                    res['time'] = float(received_message[1])
                    res['status'] = received_message[2]
                    res['address'] = address

                if s is self.listener_socket:
                    if res['status'] == 'WANTED':
                        if self.state == 'HELD' or \
                                (self.state == 'WANTED' and
                                 self.request_time < res['time'] and
                                 self.request_time > 0):
                            # self.request_time > 0 because it was initializes
                            #  with -1

                            self.add_to_queue(res)

                            if verbose_flag:
                                print('\nPeer [{0}]:'.format(self.id), end=' ')
                                print(address,
                                      '({0}) joined the queue for the resource'
                                      .format(res['id']))

                        else:
                            self.lock_sock.sendto(
                                '{0} {1} {2}'.format(
                                    self.id, time(), self.state).encode(),
                                address)

                    elif res['status'] == 'JOIN' and \
                            res['id'] != self.id and \
                            res['id'] not in self.group_members:

                        self.group_members.append(res['id'])

                        if verbose_flag:
                            print('\nPeer [{0}]:'.format(self.id), end=' ')
                            print(address, '({0}) joined the group'.format(
                                res['id']))

                        self.listener_socket.sendto('{0} {1} {2}'.format(
                            self.id, time(), 'ACK').encode(), address)

                    elif res['id'] != self.id and res['status'] != 'ACK':
                        self.listener_socket.sendto('{0} {1} {2}'.format(
                            self.id, time(), 'ACK').encode(), address)

                elif s is self.join_sock:
                    if res['id'] not in self.group_members:
                        self.group_members.append(res['id'])

                    self.inputs.remove(self.join_sock)

                elif s is self.lock_sock:
                    if res['status'] == 'WANTED':
                        if self.state == 'HELD' or \
                                (self.state == 'WANTED' and
                                 self.request_time < res['time'] and
                                 self.request_time > 0):
                            # self.request_time > 0 because it was initializes
                            #  with -1

                            self.add_to_queue(res)

                        else:
                            self.lock_sock.sendto(
                                '{0} {1} {2}'.format(
                                    self.id, time(), self.state),
                                address)

                        # Only count responsed to my request
                        self.responses_to_rlock.append(res)

                        if len(self.responses_to_rlock) == len(
                                self.group_members):

                            self.state = 'HELD'
                            self.responses_to_rlock = []
                            self.inputs.remove(self.lock_sock)

    def add_to_queue(self, request: dict):
        already_in_the_queue = False

        for e in self.queue:
            if request['id'] == e['id']:
                already_in_the_queue = True

        if not already_in_the_queue:
            self.queue.append(request)
