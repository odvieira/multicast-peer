async def send(self, message: bytes, verbose_flag: bool = True) -> int:
		"""
		Args:
			message (bytes): Every package sent must be formated as follows
								[ID] [TIME] [STATUS]

			verbose_flag (bool, optional): Print to the output internal states. Defaults to True.

		Returns:
			int:    0 - all responses were received as expected
					1 - responses number were below the expected
		"""

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
			sent = sock.sendto(message, multicast_group)

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
						await asyncio.sleep(0.5)
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
			sock.close()
			return 0