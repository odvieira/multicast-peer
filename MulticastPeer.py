import asyncio
import multiprocessing
import select
import socket
import struct
import sys
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
		sock.setblocking(0)

		# Set the time-to-live for messages to 1 so they do not
		# go past the local network segment.
		ttl = struct.pack('b', 1)
		sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

		# Send data to the multicast group
		sent = sock.sendto(
			'{0} {1} {2}'.format(
				self.id, time(), 'JOIN').encode(), multicast_group)

		# Sockets from which we expect to read
		inputs=[sock]

		# Sockets to which we expect to write
		outputs=[]

		while inputs:
			readable, writable, exceptional = select.select(\
				inputs, outputs, inputs, 0)
			
			if len(readable) == 0:
				await asyncio.sleep(0.01)

			for s in readable:
				if s is sock:
					try:
						data, address=s.recvfrom(4096)
					except:
						raise
					else:
						if not data:
							await asyncio.sleep(0.01)
							continue

						received_message=data.decode().split(' ')

						res={}

						res['id']=received_message[0]
						res['time']=received_message[1]
						res['status']=received_message[2]
						res['address']=address

					if res['id'] not in self.group_members:
						self.group_members.append(res['id'])

	async def active(self):
		while True:
			if self.pipe_end.poll():
				try:
					command_received = self.pipe_end.recv()
				except EOFError:
					self.pipe_end.close()
					exit(0)
				else:
					if command_received == 'JOIN':
						await self.join()
					if command_received == 'RLOCK':
						await self.request_lock()

			else:
				await asyncio.sleep(0.2)

	def release_lock(self):
		pass

	async def request_lock(self, verbose_flag: bool = True) -> int:
		"""
		Args:
			message (bytes): Every package sent must be formated as follows
								[ID] [TIME] [STATUS]

			verbose_flag (bool, optional): Print to the output internal states. Defaults to True.

		Returns:
			int:    0 - all responses were received as expected
							1 - responses number were below the expected
		"""

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
		sock.setblocking(0)

		# Set the time-to-live for messages to 1 so they do not
		# go past the local network segment.
		ttl = struct.pack('b', 1)
		sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

		try:
			# Send data to the multicast group
			sent = sock.sendto(msg, multicast_group)
		except:
			raise
		else:
			# Sockets from which we expect to read
			inputs=[sock]

			# Sockets to which we expect to write
			outputs=[]

			while inputs:
				readable, writable, exceptional = select.select(\
					inputs, outputs, inputs, 0)
				
				if len(readable) == 0:
					await asyncio.sleep(0.01)

				for s in readable:
					if s is sock:
						try:
							data, address=s.recvfrom(4096)
						except:
							raise
						else:
							if not data:
								await asyncio.sleep(0.01)
								continue

							received_message=data.decode().split(' ')

							res={}

							res['id']=received_message[0]
							res['time']=received_message[1]
							res['status']=received_message[2]
							res['address']=address

							if res['status'] == 'WANTED':
								if self.state == 'HELD' or \
										(self.state == 'WANTED' and \
											self.request_time < res['time'] and \
												self.request_time > 0):
												# self.request_time > 0 because it was initializes
												#  with -1
									self.queue.append(res)
								else:
									sock.sendto(
										'{0} {1} {2}'.format(
											self.id, time(), self.state),
										address)

							self.responses.append(res)

							if len(self.responses) == len(self.group_members):
								self.state = 'HELD'
								self.responses = []
								inputs.remove(sock)

		finally:
			sock.close()
		
		return 0


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
		outputs=[]

		while inputs:
			# Wait for at least one of the sockets to be
			# ready for processing

			try:
				readable, writable, exceptional = select.select(\
					inputs, outputs, inputs, 0)
			except ValueError:
				pass

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

						if newmsg['status'] == 'JOIN' and \
								newmsg['id'] != self.id and \
								newmsg['id'] not in self.group_members:

							self.group_members.append(newmsg['id'])

							if verbose_flag:
								print('\nPeer [{0}]:'.format(self.id), end=' ')
								print(address, '({0}) joined the group'.format(
									newmsg['id']))

							sock.sendto('{0} {1} {2}'.format(self.id, time(), 'ACK')
										.encode(), address)

						elif newmsg['id'] != self.id and newmsg['status'] != 'ACK':
							if verbose_flag:
								print('\nPeer [{0}]:'.format(self.id), end=' ')
								print('received {} bytes from {}'.format(
									len(data), address))
								print(data)

							sock.sendto('{0} {1} {2}'.format(self.id, time(), 'ACK')
										.encode(), address)

					except:
						raise
