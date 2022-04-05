import socket
import struct

class Listener():
    def __init__(self):
        pass

    def run(self):
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

                elif newmsg['status'] == 'JOIN' and newmsg['id'] != self.id:
                    self.add_group_member(newmsg['id'])
                    print('\nPeer [{0}]:'.format(self.id), end=' ')
                    print(address,'({0}) joined the group'.format(newmsg['id']))

                else:
                    if verbose_flag:                        
                        print('\nPeer [{0}]:'.format(self.id), end=' ')
                        print('received {} bytes from {}'.format(
                        len(data), address))
                        print(data)

            except socket.timeout:
                print('\nPeer [{0}]:'.format(self.id), end=' ')
                print('timed out, no more responses')
                break
            except Exception:
                raise Exception

        return

        