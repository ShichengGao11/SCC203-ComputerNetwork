import os
import socket
import time
import base64

cacheDict = {}


def handleReq(clientSocket):
    # receive the data
    recvData = clientSocket.recv(4096).decode()
    try:
        # get the type of request(GET/DELETE/PUT)
        requestType = recvData.split()[0]
        # print(requestType)
        filePath = recvData.split()[1].split("//")[1].replace('/', '')
        print("accept request: " + requestType + " to " + filePath)
    except:
        return

    if requestType == "GET":
        try:  # try to find the file in the cache
            cachePath = cacheDict[filePath[:100]]

            # open the file in the cache
            with open(cachePath, 'rb') as f:
                cacheObject = f.read()
            print("file is found in the cache")

            # send the file to the client
            clientSocket.sendall(cacheObject)

        except Exception as e:  # file is not found in the cache
            print("file is not found in the cache, send the request to the server")
            # create socket to connect to the server
            serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            serverAddr = (filePath, 80)
            try:
                # connect to the server
                serverSocket.connect(serverAddr)

                # send the request to the server
                serverSocket.sendall(recvData.encode())

                # get the response from server
                response = b''
                # since the response may be extremely large, we need a loop to get the response
                while True:
                    data = serverSocket.recv(1024)
                    if not data:
                        break
                    response += data

                # save the response to the cache
                writePath = 'cache/' + base64.urlsafe_b64encode(filePath[:100].encode()).decode()
                with open(writePath, 'wb') as f:
                    f.write(response)

                # save the path in to the dict for the next request
                cacheDict[filePath[:100]] = writePath

                # send the response to the client
                clientSocket.sendall(response)
                print("request send to client")
            except Exception as e:
                print(e)
            finally:
                # close the socket
                serverSocket.close()

    else:  # Put or Delete
        serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # get the server name
        serverName = filePath

        # connect to the server
        serverSocket.connect((serverName, 80))  # the

        # send the data to the server
        serverSocket.sendall(recvData.encode("utf-8"))

        # receive the response from the server
        response = b''
        # since the response may be extremely large, we need a loop to get the response
        while True:
            data = serverSocket.recv(1024)
            if not data:
                break
            response += data

        # send the response message to the client
        clientSocket.sendall(response)
        print("response send to client")


def startProxy(port):
    # create proxy server socket
    proxyServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # bind the port
    proxyServerSocket.bind(("", port))

    # Continuously listen for connections to proxy server socket
    proxyServerSocket.listen(0)

    if not os.path.exists('cache'):
        os.mkdir('cache')
    else:
        print('load cache')
        for x in os.listdir('cache'):
            cacheDict[base64.urlsafe_b64decode(x).decode()] = 'cache/' + x
        print(cacheDict)

    while True:
        try:
            print("Proxy is waiting for connecting...")
            clientSocket, addr = proxyServerSocket.accept()
            print("Connect established")

            # call the handleReq function
            handleReq(clientSocket)

            # close the client socket
            clientSocket.close()
        except Exception as e:
            print("error: {0}".format(e))
            break

    # close the proxy server socket
    proxyServerSocket.close()


if __name__ == '__main__':
    while True:
        try:
            port = int(input("choose a port number over 1024:"))
        except ValueError:  # the input is not an integer
            print("Please input 80an integer rather than {0}".format(type(port)))
            continue
        else:
            if port <= 1024 or port >= 65536:
                print("Please input an integer between 1025 and 65535")
                continue
            else:
                break
    startProxy(port)
