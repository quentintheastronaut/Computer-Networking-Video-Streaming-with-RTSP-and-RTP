import sys
from time import time
HEADER_SIZE = 12

class RtpPacket:	
	header = bytearray(HEADER_SIZE)
	
	# hàm tạo đối tường Rtp Packet
	def __init__(self):
		pass
		
	# hàm đống gói RTP packet với cái header và dữ liệu 
	def encode(self, version, padding, extension, cc, seqnum, marker, pt, ssrc, payload):
		"""Encode the RTP packet with header fields and payload."""
		timestamp = int(time())
		header = bytearray(HEADER_SIZE)
		#--------------
		# TO COMPLETE
		#--------------
		# Fill the header bytearray with RTP header fields
		
		# header[0] = [2 bits version][1 bit padding][1bit extension][4bits cc]
		# Total 8 bits
		self.header[0] = version << 6
		self.header[0] = self.header[0] | padding << 5
		self.header[0] = self.header[0] | extension << 4
		self.header[0] = self.header[0] | cc

		# header[1] = [1bit marker][7bits pt]
		self.header[1] = marker << 7
		self.header[1] = self.header[1] | pt

		self.header[2] = (seqnum >> 8)& 0xFF
		self.header[3] = seqnum & 0xFF

		self.header[4] = (timestamp >> 24) 
		self.header[5] = (timestamp >> 16) & 0xFF
		self.header[6] = (timestamp >> 8)& 0xFF
		self.header[7] = timestamp & 0xFF

		self.header[8] = (ssrc >> 24 )
		self.header[9] = (ssrc >> 16 ) & 0xFF
		self.header[10] = (ssrc >> 8)& 0xFF
		self.header[11] = ssrc & 0xFF

		# Get the payload from the argument
		# self.payload = ...
		self.payload = payload
		
	# hàm để mở gói RTP packet
	def decode(self, byteStream):
		"""Decode the RTP packet."""
		self.header = bytearray(byteStream[:HEADER_SIZE])
		self.payload = byteStream[HEADER_SIZE:]
	
	#
	def version(self):
		"""Return RTP version."""
		return int(self.header[0] >> 6)
	
	def seqNum(self):
		"""Return sequence (frame) number."""
		seqNum = self.header[2] << 8 | self.header[3]
		print("Rtp Packet: " +str(int(seqNum)))
		return int(seqNum)
	
	def timestamp(self):
		"""Return timestamp."""
		timestamp = self.header[4] << 24 | self.header[5] << 16 | self.header[6] << 8 | self.header[7]
		return int(timestamp)
	
	def payloadType(self):
		"""Return payload type."""
		pt = self.header[1] & 127
		return int(pt)
	
	def getPayload(self):
		"""Return payload."""
		return self.payload
		
	def getPacket(self):
		"""Return RTP packet."""
		return self.header + self.payload