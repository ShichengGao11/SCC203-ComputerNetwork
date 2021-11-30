#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import socket
import os
import sys
import struct
import time
import select
import binascii

ICMP_ECHO_REQUEST = 8  # ICMP type code for echo request messages
ICMP_ECHO_REPLY = 0  # ICMP type code for echo reply messages

default_count = 4


def icmpTypeCodeHandler(return_type, code):
    if return_type == 0:
        if code == 0:
            return "Echo Reply"
    elif return_type == 3:
        if code == 0:
            return "Destination Network Unreachable"
        elif code == 1:
            return "Destination Host Unreachable"
        elif code == 2:
            return "Protocol Unreachable"
        elif code == 3:
            return "Port Unreachable"
        elif code == 4:
            return "Fragmentation needed but no frag. bit set"
        elif code == 5:
            return "Source routing failed"
        elif code == 6:
            return "Destination network unknown"
        elif code == 7:
            return "Destination host unknown"
        elif code == 8:
            return "Source host isolated (obsolete)"
        elif code == 9:
            return "Destination network administratively prohibited"
        elif code == 10:
            return "Destination host administratively prohibited"
        elif code == 11:
            return "Network unreachable for TOS"
        elif code == 12:
            return "Host unreachable for TOS"
        elif code == 13:
            return "Communication administratively prohibited by filtering"
        elif code == 14:
            return "Host precedence violation"
        elif code == 15:
            return "Precedence cutoff in effect"
    elif return_type == 4:
        if code == 0:
            return "Source quench"
    elif return_type == 5:
        if code == 0:
            return "Redirect for network"
        elif code == 1:
            return "Redirect for host"
        elif code == 2:
            return "Redirect for TOS and network"
        elif code == 3:
            return "Redirect for TOS and host"
    elif return_type == 8:
        return "Echo request"
    elif return_type == 9:
        return "Router advertisement"
    elif return_type == 10:
        return "Route solicitation"
    elif return_type == 11:
        if code == 0:
            return "TTL equals 0 during transit"
        elif code == 1:
            return "TTL equals 0 during reassembly"
    elif return_type == 12:
        if code == 0:
            return "IP header bad (catchall error)"
        elif code == 1:
            return "Required options missing"
    elif return_type == 13:
        return "Timestamp request (obsolete)"
    elif return_type == 14:
        return "Timestamp reply (obsolete)"
    elif return_type == 15:
        return "Information request (obsolete)"
    elif return_type == 16:
        return "Information reply (obsolete)"
    elif return_type == 17:
        return "Address mask request"
    elif return_type == 18:
        return "Address mask reply"


def checksum(string):
    csum = 0
    countTo = (len(string) // 2) * 2
    count = 0

    while count < countTo:
        thisVal = string[count + 1] * 256 + string[count]
        csum = csum + thisVal
        csum = csum & 0xffffffff
        count = count + 2

    if countTo < len(string):
        csum = csum + string[len(string) - 1]
        csum = csum & 0xffffffff

    csum = (csum >> 16) + (csum & 0xffff)
    csum = csum + (csum >> 16)
    answer = ~csum
    answer = answer & 0xffff
    answer = answer >> 8 | (answer << 8 & 0xff00)

    answer = socket.htons(answer)

    return answer


def receiveOnePing(icmpSocket, destinationAddress, ID, timeout):
    # 1. Wait for the socket to receive a reply
    reply = select.select([icmpSocket], [], [icmpSocket], timeout)

    # 2. Once received, record time of receipt, otherwise, handle a timeout
    receive_time = time.time()
    if reply[0] == [] and reply[1] == [] and reply[2] == []:  # if reply is three null list, it means time out
        return -1, 0, None, None  # return receive_time = -1 to identify that time out

    # 3. Compare the time of receipt to time of sending, producing the total network delay
    # The total network delay is produced in doOnePing
    receive_packet = icmpSocket.recv(4096)
    # send_time = struct.unpack('d', receive_packet[28:36])[0]
    # delay = receive_time - send_time

    # 4. Unpack the packet header for useful information, including the ID
    header = receive_packet[20:28]
    return_type, code, check_sum, receiveID, sequence = struct.unpack('bbHHh', header)
    TTL = struct.unpack('b', receive_packet[8:9])[0]
    # print(ID, receiveID)
    # 5. Check that the ID matches between the request and reply
    if ID != receiveID:
        print("receive ID does not equal to ID")

    # 6. Return total network delay
    return receive_time, TTL, return_type, code


def sendOnePing(icmpSocket, destinationAddress, ID):
    packet_type = ICMP_ECHO_REQUEST
    code = 0
    check_sum = 0
    sequence = 0

    # 1. Build ICMP header
    header = struct.pack("bbHHh", packet_type, code, check_sum, ID, sequence)
    data = struct.pack('d', time.time())
    packet = header + data

    # 2. Checksum ICMP packet using given function
    check_sum = checksum(packet)

    # 3. Insert checksum into packet
    header = struct.pack("bbHHh", packet_type, code, check_sum, ID, sequence)
    packet = header + data

    # 4. Send packet using socket
    # two way below can be used to send the packet
    # (1) connect to the destination before send the packet
    # icmpSocket.connect((destinationAddress, 80))
    # icmpSocket.send(packet)
    # (2) send the packet directly
    icmpSocket.sendto(packet, (destinationAddress, 80))

    # 5. Record time of sending
    send_time = time.time()
    return send_time


def doOnePing(destinationAddress, timeout):
    ID = os.getpid()

    # 1. Create ICMP socket
    my_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.getprotobyname('icmp'))

    # 2. Call sendOnePing function
    send_time = sendOnePing(icmpSocket=my_socket, destinationAddress=destinationAddress, ID=ID)

    # 3. Call receiveOnePing function
    receive_time, TTL, return_type, code = receiveOnePing(icmpSocket=my_socket, destinationAddress=destinationAddress,
                                                          ID=ID, timeout=timeout)
    if receive_time == -1:
        delay = -1
    else:
        delay = receive_time - send_time
    msg = icmpTypeCodeHandler(return_type, code)

    # 4. Close ICMP socket
    my_socket.close()

    # 5. Return total network delay
    return delay, TTL, return_type, code, msg


def ping(host, timeout=1, count=default_count):
    delay_list = []

    # 1. Look up hostname, resolving it to an IP address
    host_IP_address = socket.gethostbyname(host)
    print("ping %s [%s] with 8 bytes data" % (host, host_IP_address))
    # 2. Call doOnePing function, approximately every second
    for i in range(count):
        # print("Ping to %s..." % self.target_host, )
        delay, TTL, return_type, code, msg = doOnePing(host_IP_address, timeout)
        if delay == -1 or delay < 0:
            print("Ping failed. (timeout within %ssec.) %s" % (timeout, msg))
        else:
            print("Get ping in %0.4fms TTL = %f" % (delay * 1000, TTL))
            delay_list.append(delay * 1000)
        time.sleep(1)  # every second

    # 3. Print out the returned delay
    if delay_list:
        average_delay = sum(delay_list) / len(delay_list)
        max_delay = max(delay_list)
        min_delay = min(delay_list)
        print("\nmax = %0.4fms min = %0.4fms avg = %0.4fms" % (max_delay, min_delay, average_delay))
    else:
        print("failed connect")

    print("send = " + str(count) + " receive = " + str(len(delay_list)) + " loss = " +
          str(count - len(delay_list)) + " (" + str((count - len(delay_list)) / count * 100) + "% loss)")

    # 4. Continue this process until stopped


if __name__ == '__main__':
    # ping("www.google.com")
    # ping("lancaster.ac.uk")
    # ping("www.ed.gov")
    # ping("www.baidu.com")
    while True:
        host = input("please input the IP or host name(both of them are accepted): ")

        try:
            timeout = int(input("please input the time out: "))
        except Exception as e:
            print("please input an integer number")
            continue

        try:
            count = int(input("please input the times to ping: "))
        except Exception as e:
            print("please input an integer number")
            continue

        ping(host, timeout, count)
        break
