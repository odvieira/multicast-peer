import socket
import struct

class MulticastPeer:
    def __init__(self, group:str='228.5.6.7', port:int=6789):
        self.group = group
        self.port = port
        pass

    def AcquireLock(self, resource):
        pass

    def Send(self, msg:bytes):
        message = msg
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
            print('sending {!r}'.format(message))
            sent = sock.sendto(message, multicast_group)

            # Look for responses from all recipients
            while True:
                print('waiting to receive')
                try:
                    data, server = sock.recvfrom(16)
                except socket.timeout:
                    print('timed out, no more responses')
                    break
                else:
                    print('received {!r} from {}'.format(
                        data, server))

        finally:
            print('closing socket')
            sock.close()

        return

    def Listen(self):
        multicast_group = self.group
        server_address = (self.group, self.port)

        # Create the socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Bind to the server address
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
            print('\nwaiting to receive message')
            data, address = sock.recvfrom(1024)

            print('received {} bytes from {}'.format(
                len(data), address))
            print(data)

            print('sending acknowledgement to', address)
            sock.sendto(b'ack', address)

        return


        