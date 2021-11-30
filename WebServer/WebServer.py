#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import socket
import sys
import threading


sem = threading.Semaphore(3)
def handleRequest(tcpSocket):
	with sem:
		# print("Client connect successfully")
		try:
			# 1. Receive request message from the client on connection socket
			clientRequest = tcpSocket.recv(4096)
			requestMsg_utf_8 = clientRequest.decode()
			requestMsgList = requestMsg_utf_8.split("\r\n")
			# print(clientRequest)

			# 2. Extract the path of the requested object from the message (second part of the HTTP header)
			path = requestMsgList[0].split()[1].split('/')[1]

			# 3. Read the corresponding file from disk
			file = open(path, 'r', encoding='utf-8')
			# print(path)
			# file404 = open("404.html", encoding='utf-8')
			# 4. Store in temporary buffer
			# 5. Send the correct HTTP response error
		except OSError:
			file404 = open("404.html", 'r', encoding='utf-8')
			print("404 Not Found")
			header = "HTTP/1.1 404 Not Found\r\n"
			content = file404.read()
			file404.close()
		except Exception:
			fileError = open("error.html", 'r', encoding = 'utf-8')
			print("400 Error")
			header = "HTTP/1.1 400 Error\r\n"
			content = fileError.read()
			fileError.close()
		else:
			# file = open(path, encoding='utf-8')
			print("200 OK")
			header = "HTTP/1.1 200 OK\r\n"
			content = file.read()
			file.close()

		# 6. Send the content of the file to the socket
		try:
			contentLength = "Content length: " + str(len(content)) + '\r\n'
			contentType = "Content type: txt/html\r\n"
			respondMsg = header + contentType + "\r\n" + content
			tcpSocket.sendall(respondMsg.encode())
		except ConnectionResetError:
			tcpSocket.close()

			# 7. Close the connection socket
		tcpSocket.close()


def startServer(serverAddress, serverPort):
	print("Start server at 127.0.0.1:%d\n" % serverPort)
	# 1. Create server socket
	while True:
		serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

		# 2. Bind the server socket to server address and server port
		serverSocket.bind((serverAddress, serverPort))
		# 3. Continuously listen for connections to server socket
		serverSocket.listen(1)

		# 4. When a connection is accepted, call handleRequest function, passing new connection socket (see https://docs.python.org/3/library/socket.html#socket.socket.accept)
		tcpSocket, address = serverSocket.accept()
		# handleRequest(tcpSocket)
		t = threading.Thread(target=handleRequest, args= (tcpSocket,))  # implement the additional feature:
		t.start()
		# 5. Close server socket
		serverSocket.close()


if __name__ == '__main__':
	while True:
		try:
			portNum = int(input("Please input the port number: "))
		except Exception:
			print("Please input an integer")
			continue
		if portNum < 0 or portNum >= 65536:
			print("The port number should between 0 and 65536")
			continue
		break
	startServer("", portNum)

