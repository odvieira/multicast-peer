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

	def __init__(self, id, pipe_end: multiprocessing.Pipe = None, \
		group: str = '228.5.6.7', port: int = 6789):
		self.group = group
		self.port = port
		self.state = 'RELEASED'
		self.queue = []
		self.group_members = []
		self.id = str(id)
		self.responses = []
		self.pipe_end = pipe_end
		self.request_time = -1.0

	async def join(self):
		multicast_group = (self.group, self.port)

		# Create the datagram socket
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

		# The socket does not block
		# indefinitely when trying to receive data.
		sock.settimeout(1)

		# Set the time-to-live for messages to 1 so they do not
		# go past the local network segment.
		ttl = struct.pack('b', 1)
		sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

		# Send data to the multicast group
		sent = sock.sendto(
			'{0} {1} {2}'.format(
				self.id, time(), 'JOIN').encode(), multicast_group)

		while True:
			try:
				data, address = sock.recvfrom(4096, socket.MSG_DONTWAIT)
			except socket.timeout:
				sock.close()
				return 1
			else:
				if not data:
						await asyncio.sleep(0.5)
						continue

				print('\nPeer [{0}]:'.format(self.id), end=' ')
				print('{!r} received from {}'.format(data, address))

			finally:
				sock.close()
				return 0

	async def active(self):
		while True:
			if self.pipe_end.poll():
				try:
					command_received = self.pipe_end.recv()
				except EOFError:
					self.pipe_end.close()
					exit(0)
				else:
					print('comando: ', command_received)

					if command_received == 'JOIN':
						await self.join()
			else:
				await asyncio.sleep(0.2)

	async def request_lock(self, verbose_flag: bool = True) -> int:
		self.state = 'WANTED'
		self.request_time = time()

		msg = '{0} {1} {2}'.format(
			self.id, self.request_time,
			self.state).encode()

		multicast_group = (self.group, self.port)

		# Create the datagram socket
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

		# The socket does not block
		# indefinitely when trying to receive data.
		sock.settimeout(3)

		# Set the time-to-live for messages to 1 so they do not
		# go past the local network segment.
		ttl = struct.pack('b', 1)
		sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

		try:
			# Send data to the multicast group
			sent = sock.sendto(msg, multicast_group)

		except Exception:
			return 2

		else:
			while True:
				try:
					data, address=sock.recvfrom(4096, socket.MSG_DONTWAIT)
				except socket.timeout:
					sock.close()
					return 1
				else:
					if not data:
						await asyncio.sleep(0.1)
						continue

					if verbose_flag:
						print('\nPeer [{0}]:'.format(self.id), end=' ')
						print('{!r} received from {}'.format(data, address))

					received_message=data.decode().split(' ')

					res={}

					res['id']=received_message[0]
					res['time']=received_message[1]
					res['status']=received_message[2]
					res['address']=address

					self.responses.append(res)

		finally:
			if len(self.responses) == len(self.group_members):
				self.state = 'HELD'
			sock.close()
			return 0

	def release_lock(self):
		pass

	
	async def listen(self, verbose_flag: bool=True) -> None:
		"""
		Args:
			verbose_flag (bool, optional): Prints internal state.
			Defaults to True.

		Raises:
			Exception: Unknow

		Every package are formated as follows:
			[ID] [TIME] [STATUS]
		"""
		multicast_group=self.group
		server_address=(self.group, self.port)

		# Create the socket
		sock=socket.socket(
			socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

		# Non blocking socket
		sock.setblocking(0)

		# Bind to the server address
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		sock.bind(server_address)

		# Tell the operating system to add the socket to
		# the multicast group on all interfaces.
		group=socket.inet_aton(multicast_group)
		mreq=struct.pack('4sL', group, socket.INADDR_ANY)
		sock.setsockopt(
			socket.IPPROTO_IP,
			socket.IP_ADD_MEMBERSHIP,
			mreq)

		# Sockets from which we expect to read
		inputs=[sock]

		# Sockets to which we expect to write
		outputs=[self.pipe_end]

		# Outgoing message queues (socket:Queue)
		message_queues={}

		while inputs:
			# Wait for at least one of the sockets to be
			# ready for processing
			# if verbose_flag:
			# 	print('\nPeer [{0}]:'.format(self.id), end=' ')
			# 	print('waiting for the next event', file=sys.stderr)

			readable, writable, exceptional=select.select(inputs,
															outputs,
															inputs)

			# select() returns three new lists, containing subsets of
			# the contents of the lists passed in. All of the sockets
			# in the readable list have incoming data buffered and
			# available to be read. All of the sockets in the writable
			# list have free space in their buffer and can be written to.
			# The sockets returned in exceptional have had an error (the
			# actual definition of “exceptional condition” depends on
			# the platform).

			if len(readable) == 0:
				await asyncio.sleep(0.01)

			for s in readable:
				if s is sock:
					try:
						data, address=s.recvfrom(4096)

						if not data:
							await asyncio.sleep(0.01)
							continue

						received_message=data.decode().split(' ')

						newmsg={}

						newmsg['id']=received_message[0]
						newmsg['time']=received_message[1]
						newmsg['status']=received_message[2]
						newmsg['address']=address

						if newmsg['status'] == 'WANTED':
							if verbose_flag:
								print('\nPeer [{0}]:'.format(self.id), end=' ')
								print(address, '({0}) wants the resource'.format(
									newmsg['id']))

							if self.state == 'HELD' or \
									(self.state == 'WANTED' and \
										self.request_time < newmsg['time'] and \
											self.request_time > 0):
											# self.request_time > 0 because it was initializes
											#  with -1
								self.queue.append(newmsg)
							else:
								sock.sendto(
									'{0} {1} {2}'.format(
										self.id, time(), self.state),
									address)

						elif newmsg['status'] == 'JOIN' and \
								newmsg['id'] != self.id and \
								newmsg['id'] not in self.group_members:

							self.group_members.append(newmsg['id'])

							if verbose_flag:
								print('\nPeer [{0}]:'.format(self.id), end=' ')
								print(address, '({0}) joined the group'.format(
									newmsg['id']))

						elif newmsg['id'] != self.id:
							if verbose_flag:
								print('\nPeer [{0}]:'.format(self.id), end=' ')
								print('received {} bytes from {}'.format(
									len(data), address))
								print(data)

							sock.sendto('{0} {1} {2}'.format(self.id, time(), 'ACK')
										.encode(), address)

					except Exception:
						raise Exception('Unknown exception')
