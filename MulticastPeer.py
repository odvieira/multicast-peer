import os
import socket
import struct
from time import time

class MulticastPeer:
    def __init__(self, group:str='228.5.6.7', port:int=6789):
        self.group = group
        self.port = port
        self.state = 'RELEASED'

    def test(self, number_of_tries=2):
        for i in range(number_of_tries):
            self.send('{0} {1} {2}'.format(os.getpid(), time(), self.state).encode())
        

    def send(self, message:bytes):
        multicast_group = (self.group, self.port)

        # Create the datagram socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Set a timeout so the socket does not block
        # indefinitely when trying to receive data.
        sock.settimeout(0.2)

        # Set the time-to-live for messages to 1 so they do not
        # go past the local network segment.
        ttl = struct.pack('b', 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

        try:
            # Send data to the multicast group
            # print('\nPeer [{0}]:'.format(os.getpid()), end=' ')
            # print('sending {!r}'.format(message))
            sent = sock.sendto(message, multicast_group)

            # Look for responses from all recipients
            while True:
                # print('\nPeer [{0}]:'.format(os.getpid()), end=' ')
                # print('waiting to receive a response')
                try:
                    data, server = sock.recvfrom(16)
                except socket.timeout:
                    # print('\nPeer [{0}]:'.format(os.getpid()), end=' ')
                    # print('timed out, no more responses')
                    break
                else:
                    # print('\nPeer [{0}]:'.format(os.getpid()), end=' ')
                    # print('received {!r} from {}\n'.format(
                    #     data, server))
                    pass

        finally:
            # print('\nPeer [{0}]:'.format(os.getpid()), end=' ')
            # print('closing socket')
            sock.close()

        return

        
    def listen(self):
        multicast_group = self.group
        server_address = (self.group, self.port)

        # Create the socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

        # Bind to the server address
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(server_address)

        # sock.settimeout(100)

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
            # print('\nPeer [{0}]: waiting to receive message'.format(os.getpid()))

            try:
                data, address = sock.recvfrom(4096)
                received_message = data.decode().split(' ')    

                # print('\nPeer [{0}]:'.format(os.getpid()), end=' ')
                # print(received_message)

                if received_message[2] == 'RELEASED':
                    print('\nPeer [{0}]:'.format(os.getpid()), end=' ')
                    print(address,'({0}) released the resource'.format(received_message[0]))                    
                elif received_message[2] == 'WANTED':
                    print('\nPeer [{0}]:'.format(os.getpid()), end=' ')
                    print(address,'({0}) wants the resource'.format(received_message[0]))
                elif received_message[2] == 'HELD':
                    print('\nPeer [{0}]:'.format(os.getpid()), end=' ')
                    print(address, '({0}) is holding the resource'.format(received_message[0]))
                else:
                    print('\nPeer [{0}]:'.format(os.getpid()), end=' ')
                    print('received {} bytes from {}'.format(
                    len(data), address))
                    print(data)

                # print('\nPeer [{0}]:'.format(os.getpid()), end=' ') 
                # print('sending acknowledgement to', address)
                sock.sendto(b'ack', address)

            except socket.timeout:
                print('\nPeer [{0}]:'.format(os.getpid()), end=' ')
                print('timed out, no more responses')
                break
            
        return

        