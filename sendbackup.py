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
