import asyncio
import multiprocessing
import select
import socket
import struct
from time import time

class MulticastPeer():
    """
    Multicast Peer
    ----------------
    Communication protocol

    Every package sent must be formated as follows:
                                    [ID] [TIME] [STATUS]
    """

    def __init__(self, id, pipe_command: multiprocessing.Pipe = None,
                    pipe_state_snd:multiprocessing.Pipe = None,
                    group: str = '228.151.26.111', port: int = 6789):
        self.group = group
        self.port = port
        self.state = 'DISCONNECTED'
        self.queue = []
        self.group_members = []
        self.id = str(id)
        self.responses_to_alock = []
        self.pipe_end = pipe_command
        self.pipe_state = pipe_state_snd
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

        self.update_screen()

        return

    async def close(self):
        self.release_lock()

        await asyncio.sleep(0.5)

        self.leave()

        await asyncio.sleep(0.5)

        self.listener_socket.close()
        self.join_sock.close()
        self.lock_sock.close()
        self.pipe_end.close()
        self.pipe_state.close()
        self.exit = True

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

        if self.listener_socket not in self.inputs:
            self.inputs.append(self.listener_socket)

        return 0

    def leave(self):
        self.group_members = []

        self.release_lock()

        # Send data to the multicast group
        sent = self.join_sock.sendto(
            '{0} {1} {2}'.format(
                self.id, time(), 'LEAVE').encode(), self.multicast_group)

        self.change_state('DISCONNECTED')


    def join(self):
        self.group_members = []

        self.change_state('RELEASED')

        self.release_lock()
        # Send data to the multicast group
        sent = self.join_sock.sendto(
            '{0} {1} {2}'.format(
                self.id, time(), 'JOIN').encode(), self.multicast_group)
        
        if self.join_sock not in self.inputs:
            self.inputs.append(self.join_sock)

    def change_state(self, new_state:str):
        self.state = new_state
        self.update_screen()

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
                        self.join()
                    elif command_received == 'ALOCK':
                        self.acquire_lock()
                    elif command_received == 'RLOCK':
                        self.release_lock()
                    elif command_received == 'EXIT':
                        await self.close()
                        return
            else:
                await asyncio.sleep(0.1)

    def release_lock(self):
        if self.state == 'DISCONNECTED':
            return

        self.change_state('RELEASED')

        msg = '{0} {1} {2}'.format(
            self.id, self.request_time,
            self.state).encode()

        for member in self.queue:
            try:
                # Send data to the group member
                sent = self.lock_sock.sendto(msg, member['address'])
            except:
                raise

        self.queue = []
        self.responses_to_alock = []
        self.update_screen()

    def acquire_lock(self, verbose_flag: bool = True) -> None:
        """
        Args:
                        verbose_flag (bool, optional): Print to the output internal
                                                        states. Defaults to True.
        """

        if self.state == 'WANTED' or self.state == 'HELD' or \
            self.state == 'DISCONNECTED':
            return

        self.release_lock()

        self.responses_to_alock = []
        
        self.request_time = time()

        if len(self.group_members) == 0:
            self.change_state('HELD')
            return

        self.change_state('WANTED')        

        msg = '{0} {1} {2}'.format(
            self.id, self.request_time,
            self.state).encode()

        try:
            # Send data to the multicast group
            sent = self.lock_sock.sendto(msg, self.multicast_group)
        except:
            raise
        else:
            if self.lock_sock not in self.inputs:
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

            if not len(self.inputs) > 0 and not len(self.outputs) > 0:
                await asyncio.sleep(0.01)

            try:
                readable, writable, exceptional = select.select(
                    self.inputs, self.outputs, self.inputs, 0)
            except:
                raise

            if not len(readable) > 0 and not len(writable) > 0:
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

                if res['id'] == self.id or self.state == 'DISCONNECTED':
                    continue

                # Request comes in from another peer because he wants to
                # use the resource
                if s is self.listener_socket:
                    if res['status'] == 'WANTED':
                        if self.state == 'HELD' or \
                                (self.state == 'WANTED' and
                                 self.request_time < res['time'] and
                                 self.request_time > 0 and res['time'] > 0):
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
                            res['id'] not in self.group_members:

                        self.group_members.append(res['id'])
                        self.update_screen()

                        if verbose_flag:
                            print('\nPeer [{0}]:'.format(self.id), end=' ')
                            print(address, '({0}) joined the group'.format(
                                res['id']))

                        self.listener_socket.sendto('{0} {1} {2}'.format(
                            self.id, time(), 'ACK').encode(), address)
                    
                    elif res['status'] == 'LEAVE':
                        if res['id'] in self.group_members:
                            self.group_members.remove(res['id'])
                            self.update_screen()

                    elif res['id'] != self.id and res['status'] != 'ACK':
                        self.listener_socket.sendto('{0} {1} {2}'.format(
                            self.id, time(), 'ACK').encode(), address)

                elif s is self.join_sock:
                    if res['id'] not in self.group_members:
                        self.group_members.append(res['id'])
                        self.update_screen()

                # This response comes in when I request the resource and someone
                # sends back his state to me
                elif s is self.lock_sock:
                    if res['status'] == 'WANTED':
                        if self.state == 'HELD' or \
                                (self.state == 'WANTED' and
                                 self.request_time < res['time'] and
                                 self.request_time > 0 and res['time'] > 0):
                            # self.request_time > 0 because it was initializes
                            #  with -1

                            self.add_to_queue(res)

                            if not self.state == 'HELD':
                                # Only count those responses to my request that was
                                # made after my request
                                self.add_response(res)
                        else:
                            self.lock_sock.sendto(
                                '{0} {1} {2}'.format(
                                    self.id, time(), self.state),
                                address)

                    if self.state == 'WANTED':
                        if res['status'] == 'RELEASED':
                        # Only count those responses to my request that was
                        # made after my request
                            self.add_response(res)

                        if len(self.responses_to_alock) >= len(
                                self.group_members):
                            self.responses_to_alock = []
                            self.inputs.remove(self.lock_sock)
                            self.request_time = -1.0
                            self.change_state('HELD')                   


    def update_screen(self):
        q = []
        for i in self.queue:
            q.append(i['id'])

        if self.pipe_state.writable:
            self.pipe_state.send(
                'ID: {3}\nGroup: {1}\nQueue: {2}\nStatus: {0}'
                .format(self.state, self.group_members, q, self.id))

    def add_to_queue(self, request: dict):
        for e in self.queue:
            if request['id'] == e['id']:
                self.queue.remove(e)
        
        self.queue.append(request)
        self.update_screen()

    def add_response(self, request:dict):
        for e in self.responses_to_alock:
            if e['id'] == request['id']:
                self.responses_to_alock.remove(e)

        self.responses_to_alock.append(request)
