from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os

from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

class Client:
	INIT = 0
	READY = 1
	PLAYING = 2
	state = INIT

	SETUP = 0
	PLAY = 1
	PAUSE = 2
	TEARDOWN = 3

	# Initiation..
	# hàm khỏi tạo một đối tượng CLient 
	def __init__(self, master, serveraddr, serverport, rtpport, filename):
		self.master = master
		self.master.protocol("WM_DELETE_WINDOW", self.handler)
		self.createWidgets()
		self.serverAddr = serveraddr
		self.serverPort = int(serverport)
		self.rtpPort = int(rtpport)
		self.fileName = filename
		self.rtspSeq = 0
		self.sessionId = 0
		self.requestSent = -1
		self.teardownAcked = 0
		self.connectToServer()
		self.frameNbr = 0
		
	# hàm tạo giao diện với Tkinter
	def createWidgets(self):
		"""Build GUI."""
		self.master.resizable(width=True, height=True)
		self.master.configure(bg='white')

		self.label1 = Label(self.master, text="Welcome to Netflix")
		self.label1.grid(row=0, column=0, columnspan=4,padx=5, pady=5)
		
		self.load = Image.open("Netflix_logo.png")
		self.load.resize((50, 50),Image.ANTIALIAS)
		self.render = ImageTk.PhotoImage(self.load)
		
		self.img = Label(self.master, image=self.render)
		self.img.grid(row=1,columnspan=4,  padx=2, pady=2)

		self.load1 = Image.open("poster.jpg")
		self.load1.resize((50, 50),Image.ANTIALIAS)
		self.render1 = ImageTk.PhotoImage(self.load1)
		
		self.img1 = Label(self.master, image=self.render1)
		self.img1.grid(row=2,column=0,  padx=2, pady=2)

		# Create Setup button
		self.setup = Button(self.master, width=20, padx=3, pady=3)
		self.setup["text"] = "Setup"
		self.setup["command"] = self.setupMovie
		self.setup.grid(row=3, column=0, padx=2, pady=2)

		# Create Play button
		self.start = Button(self.master, width=20, padx=3, pady=3)
		self.start["text"] = "Play"
		self.start["command"] = self.playMovie
		self.start.grid(row=3, column=1, padx=2, pady=2)

		# Create Pause button
		self.pause = Button(self.master, width=20, padx=3, pady=3)
		self.pause["text"] = "Pause"
		self.pause["command"] = self.pauseMovie
		self.pause.grid(row=3, column=2, padx=2, pady=2)

		# Create Teardown button
		self.teardown = Button(self.master, width=20, padx=3, pady=3)
		self.teardown["text"] = "Teardown"
		self.teardown["command"] =  self.exitClient
		self.teardown.grid(row=3, column=3, padx=2, pady=2)

		# Create a label to display the movie
		self.label = Label(self.master, height=19)
		self.label.grid(row=2, column=1, columnspan=2, sticky=W+E+N+S, padx=5, pady=5)

		self.label5 = Label(self.master, text="You are watching: \nGattaca (1997)")
		self.label5.grid(row=2, column=3 ,padx=5, pady=5,sticky=W)

		self.label1 = Label(self.master, text="Ẹnoy your movie")
		self.label1.grid(row=8, column=0, columnspan=4,padx=5, pady=5)

		self.label1 = Label(self.master, text="How to play video")
		self.label1.grid(row=4, column=0, columnspan=4,padx=0, pady=5)
		self.label1 = Label(self.master, text="Step 1: Click Set Up")
		self.label1.grid(row=5, column=1, columnspan=4,padx=0, pady=5,sticky=W)
		self.label1 = Label(self.master, text="Step 2: Click Play to streaming movie or click Pause to pause the movie")
		self.label1.grid(row=6, column=1, columnspan=4,padx=0, pady=5,sticky=W)
		self.label1 = Label(self.master, text="Step 3: Click Teardown to turn off")
		self.label1.grid(row=7, column=1, columnspan=4,padx=0, pady=5,sticky=W)


	#hàm gọi thực thi tác vụ Set Up
	def setupMovie(self):
		"""Setup button handler."""
		if self.state == self.INIT:
			self.sendRtspRequest(self.SETUP)

	# hàm gọi để thoát khỏi window stream video
	def exitClient(self):
		"""Teardown button handler."""
		self.sendRtspRequest(self.TEARDOWN)		
		self.master.destroy() # Close the gui window
		os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT)

	# hàm gọi để pause video
	def pauseMovie(self):
		"""Pause button handler."""
		if self.state == self.PLAYING:
			self.sendRtspRequest(self.PAUSE)

	# hàm gọi để chạy video
	def playMovie(self):
		"""Play button handler."""
		if self.state == self.READY:
			# Create a new thread to listen for RTP packets
			threading.Thread(target=self.listenRtp).start()
			self.playEvent = threading.Event()
			self.playEvent.clear()
			self.sendRtspRequest(self.PLAY)


	# hàm để lắng nghe từ cổng RTP
	def listenRtp(self):
		"""Listen for RTP packets."""
		while True:
			try:
				data,addr = self.rtpSocket.recvfrom(20480)
				if data:
					rtpPacket = RtpPacket()
					rtpPacket.decode(data)
					
					currFrameNbr = rtpPacket.seqNum()
					print("Current Seq Num: " + str(currFrameNbr))

					if currFrameNbr > self.frameNbr: # Discard the late packet
						self.frameNbr = currFrameNbr
						self.updateMovie(self.writeFrame(rtpPacket.getPayload()))
			except:
				# Stop listening upon requesting PAUSE or TEARDOWN
				
				if self.playEvent.isSet():
					break

				# Upon receiving ACK for TEARDOWN request,
				# close the RTP socket
				if self.teardownAcked == 1:
					self.rtpSocket.shutdown(socket.SHUT_RDWR)
					self.rtpSocket.close()
					break

	# hàm để chuyển từ một frame nhận được thành 1 file ảnh để xuất ra.
	def writeFrame(self, data):
		"""Write the received frame to a temp image file. Return the image file."""
		cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
		file = open(cachename, "wb")
		file.write(data)
		file.close()
		
		return cachename

	# hàm để update các ảnh liên tục tạo thành một videp
	def updateMovie(self, imageFile):
		"""Update the image file as video frame in the GUI."""
		photo = ImageTk.PhotoImage(Image.open(imageFile))
		self.label.configure(image = photo, height=288) 
		self.label.image = photo


	# hàm gọi để kết nối tới Server
	def connectToServer(self):
		"""Connect to the Server. Start a new RTSP/TCP session."""
		self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			self.rtspSocket.connect((self.serverAddr, self.serverPort))
		except:
			tkinter.messagebox.showwarning('Connection Failed', 'Connection to \'%s\' failed.' %self.serverAddr)
	
	# hàm  gọi để gữi đi một yêu cầu RTSP 
	def sendRtspRequest(self, requestCode):
		"""Send RTSP request to the server."""
		#-------------
		# TO COMPLETE
		#-------------

		# Setup request
		if requestCode == self.SETUP and self.state == self.INIT:
			threading.Thread(target=self.recvRtspReply).start()
			# Update RTSP sequence number.
			# ...
			self.rtspSeq = 1

			# Write the RTSP request to be sent.
			# request = ...
			request = "SETUP " + str(self.fileName) + "\n" + str(self.rtspSeq) + "\n" + " RTSP/1.0 " +str(self.sessionId)+" " + str(self.rtpPort)
			byt = request.encode()
			self.rtspSocket.send(byt)
			# Keep track of the sent request.
			# self.requestSent = ...
			self.requestSent = self.SETUP


			print("\nC: SETUP "+str(self.fileName) + " RTSP/1.0")
			print("C: CSeq: " + str(self.rtspSeq))
			print("C: Transport: RTP/UDP;client_port= "+str(self.serverPort))


		# Play request
		elif requestCode == self.PLAY and self.state == self.READY:
			# Update RTSP sequence number.
			# ...
			self.rtspSeq = self.rtspSeq + 1
			# Write the RTSP request to be sent.
			# request = ...
			request = "PLAY " + str(self.fileName) + "\n" + str(self.rtspSeq) + "\n" + " RTSP/1.0 " +str(self.sessionId)+" " + str(self.rtpPort)
			byt = request.encode()
			self.rtspSocket.send(byt)
			
			# Keep track of the sent request.
			# self.requestSent = ...
			self.requestSent = self.PLAY

			print("\nC: PLAY "+str(self.fileName) + " RTSP/1.0")
			print("C: CSeq: " + str(self.rtspSeq))
			print("C: Session "+str(self.sessionId))

		# Pause request
		elif requestCode == self.PAUSE and self.state == self.PLAYING:
			# Update RTSP sequence number.
			# ...
			self.rtspSeq = self.rtspSeq + 1
			# Write the RTSP request to be sent.
			# request = ...
			request = "PAUSE " + str(self.fileName) + "\n" + str(self.rtspSeq) + "\n" + " RTSP/1.0 " +str(self.sessionId)+" " + str(self.rtpPort)
			byt = request.encode()
			self.rtspSocket.send(byt)
			
			# Keep track of the sent request.
			# self.requestSent = ...
			self.requestSent = self.PAUSE

			print("\nC: PAUSE "+str(self.fileName) + " RTSP/1.0")
			print("C: CSeq: " + str(self.rtspSeq))
			print("C: Session "+str(self.sessionId))

		# Resume request


		# Teardown request
		elif requestCode == self.TEARDOWN and not self.state == self.INIT:
			# Update RTSP sequence number.
			# ...
			self.rtspSeq = self.rtspSeq + 1
			# Write the RTSP request to be sent.
			# request = ...
			request = "TEARDOWN " + str(self.fileName) + "\n" + str(self.rtspSeq) + "\n" + " RTSP/1.0 " +str(self.sessionId)+" " + str(self.rtpPort)
			byt = request.encode()
			self.rtspSocket.send(byt)
			
			# Keep track of the sent request.
			# self.requestSent = ...
			self.requestSent = self.TEARDOWN

			print("\nC: TEARDOWN "+str(self.fileName) + " RTSP/1.0")
			print("C: CSeq: " + str(self.rtspSeq))
			print("C: Session "+str(self.sessionId))
		else:
			return

		# Send the RTSP request using rtspSocket.
		# ...
		
	# hàm nhận về phản hồi các yêu cầu RTSP từ server
	def recvRtspReply(self):
		"""Receive RTSP reply from the server."""
		while True:
			reply = self.rtspSocket.recv(1024)

			if reply:
				self.parseRtspReply(reply)

			# Close the RTSP socket upon requesting Teardown
			if self.requestSent == self.TEARDOWN:
				self.rtspSocket.shutdown(socket.SHUT_RDWR)
				self.rtspSocket.close()
				break


	# hàm để phân tích cú pháp của phản hồi các yêu cầu RTSP
	def parseRtspReply(self, data):
		

		"""Parse the RTSP reply from the server."""
		lines = data.decode().split('\n')
		seqNum = int(lines[1].split(' ')[1])

		# Process only if the server reply's sequence number is the same as the request's
		if seqNum == self.rtspSeq:
			session = int(lines[2].split(' ')[1])
			# New RTSP session ID
			if self.sessionId == 0:
				self.sessionId = session

			# Process only if the session ID is the same
			if self.sessionId == session:
				if int(lines[0].split(' ')[1]) == 200:
					if self.requestSent == self.SETUP:
						#-------------
						# TO COMPLETE
						#-------------
						# Update RTSP state.
		
						# self.state = ...
						self.state = self.READY
						# Open RTP port.
						#self.openRtpPort()
						self.openRtpPort()

					elif self.requestSent == self.PLAY:
						 self.state = self.PLAYING
						 
					elif self.requestSent == self.PAUSE:
						 self.state = self.READY

						# The play thread exits. A new thread is created on resume.
						 self.playEvent.set()

					elif self.requestSent == self.TEARDOWN:
						# self.state = ...

						# Flag the teardownAcked to close the socket.
						self.teardownAcked = 1

	# hàm để mở một RTP port
	def openRtpPort(self):
		"""Open RTP socket binded to a specified port."""
		#-------------
		# TO COMPLETE
		#-------------
		# Create a new datagram socket to receive RTP packets from the server
		# self.rtpSocket = ...

		self.rtpSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
		# Set the timeout value of the socket to 0.5sec
		# ...
		self.rtpSocket.settimeout(0.5)
		try:
			#self.rtpSocket.connect(self.serverAddr,self.rtpPort)
			self.rtpSocket.bind((self.serverAddr,self.rtpPort))   # WATCH OUT THE ADDRESS FORMAT!!!!!  rtpPort# should be bigger than 1024
			#self.rtpSocket.listen(5)
		except:
			tkinter.messagebox.showwarning('Unable to Bind', 'Unable to bind PORT=%d' %self.rtpPort)

	# hàm để thực thi tác vụ đóng cái cửa sổ 
	def handler(self):
		"""Handler on explicitly closing the GUI window."""
		self.pauseMovie()
		if tkinter.messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
			self.exitClient()
		else: # When the user presses cancel, resume playing.
			self.playMovie()