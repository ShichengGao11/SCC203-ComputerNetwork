from socket import *

serverName = '127.0.0.1'
serverPort = 8000
clientSocket1 = socket(AF_INET, SOCK_STREAM)
clientSocket2 = socket(AF_INET, SOCK_STREAM)
clientSocket1.connect((serverName, serverPort))
clientSocket2.connect((serverName, serverPort))
request = 'GET /index.html HTTP/1.1\r\n'
clientSocket1.send(request.encode())
clientSocket2.send(request.encode())
response1 = clientSocket1.recv(1024)
response2 = clientSocket2.recv(1024)
print('Response1 from server: ', response1.decode())
print('Response2 from server: ', response2.decode())
clientSocket1.close()
clientSocket2.close()