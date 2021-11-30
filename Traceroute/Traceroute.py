#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import socket
import os
import sys
import struct
import time
import select
import binascii


def icmpTypeCodeHandler(return_type, code):
    msg = ""
    if return_type == -1:
        if code == -1:
            msg = "Request timed out"
    elif return_type == 0:
        if code == 0:
            msg = "Echo Reply"
    elif return_type == 3:
        if code == 0:
            msg = "Destination Network Unreachable"
        elif code == 1:
            msg = "Destination Host Unreachable"
        elif code == 2:
            msg = "Protocol Unreachable"
        elif code == 3:
            msg = "Port Unreachable"
        elif code == 4:
            msg = "Fragmentation needed but no frag. bit set"
        elif code == 5:
            msg = "Source routing failed"
        elif code == 6:
            msg = "Destination network unknown"
        elif code == 7:
            msg = "Destination host unknown"
        elif code == 8:
            msg = "Source host isolated (obsolete)"
        elif code == 9:
            msg = "Destination network administratively prohibited"
        elif code == 10:
            msg = "Destination host administratively prohibited"
        elif code == 11:
            msg = "Network unreachable for TOS"
        elif code == 12:
            msg = "Host unreachable for TOS"
        elif code == 13:
            msg = "Communication administratively prohibited by filtering"
        elif code == 14:
            msg = "Host precedence violation"
        elif code == 15:
            msg = "Precedence cutoff in effect"
    elif return_type == 4:
        if code == 0:
            msg = "Source quench"
    elif return_type == 5:
        if code == 0:
            msg = "Redirect for network"
        elif code == 1:
            msg = "Redirect for host"
        elif code == 2:
            msg = "Redirect for TOS and network"
        elif code == 3:
            msg = "Redirect for TOS and host"
    elif return_type == 8:
        msg = "Echo request"
    elif return_type == 9:
        msg = "Router advertisement"
    elif return_type == 10:
        msg = "Route solicitation"
    elif return_type == 11:
        if code == 0:
            msg = "TTL equals 0 during transit"
        elif code == 1:
            msg = "TTL equals 0 during reassembly"
    elif return_type == 12:
        if code == 0:
            msg = "IP header bad (catchall error)"
        elif code == 1:
            msg = "Required options missing"
    elif return_type == 13:
        msg = "Timestamp request (obsolete)"
    elif return_type == 14:
        msg = "Timestamp reply (obsolete)"
    elif return_type == 15:
        msg = "Information request (obsolete)"
    elif return_type == 16:
        msg = "Information reply (obsolete)"
    elif return_type == 17:
        msg = "Address mask request"
    elif return_type == 18:
        msg = "Address mask reply"
    return msg

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


def receiveOnePingICMP(tracerouteSocket, destinationAddress, ID, timeout):
    # 1. Wait for the socket to receive a reply
    reply = select.select([tracerouteSocket], [], [], timeout)

    # 2. Once received, record time of receipt, otherwise, handle a timeout
    receive_time = time.time()

    if reply[0] == [] and reply[1] == [] and reply[2] == []:  # timeout
        return -1, -1, -1, None

    # 3. Compare the time of receipt to time of sending, producing the total network delay
    receive_packet, receive_address = tracerouteSocket.recvfrom(4096)

    # 4. Unpack the packet header for useful information, including the ID
    header = receive_packet[20:28]
    return_type, code, check_sum, receive_ID, sequence = struct.unpack('bbHHh', header)

    # TTL = struct.unpack('b', receivePacket[8:9])[0]

    # 5. Check that the ID matches between the request and reply
    # print(ID == receiveID)

    # 6. Return total network delay
    return receive_time, return_type, code, receive_address[0]


def sendOnePingICMP(traceroute_socket, destination_address, ID):
    # 1. Build header
    icmp_type = 8
    code = 0
    check_sum = 0
    sequence = 0

    header = struct.pack('bbHHh', icmp_type, code, check_sum, ID, sequence)
    data = struct.pack('d', time.time())

    # 2. Checksum packet using given function
    packet = header + data
    check_sum = checksum(packet)

    # 3. Insert checksum into packet
    header = struct.pack('bbHHh', icmp_type, code, check_sum, ID, sequence)
    packet = header + data

    # 4. Send packet using socket
    # Two way to send a packet
    # (1) connect the socket before send the packet
    # tracerouteSocket.connect((destinationAddress, 80))
    # tracerouteSocket.send(packet)
    # (2) send the packet directly
    traceroute_socket.sendto(packet, (destination_address, 40000))

    # 5. Record time of sending
    send_time = time.time()
    return send_time


def doOnePingICMP(destination_address, timeout, protocol, TTL):
    global loss_packet_cnt, receive_packet_cnt
    ID = os.getpid()

    # 1. Create a socket

    traceroute_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.getprotobyname(protocol))


    traceroute_socket.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, TTL)
    # traceroute_socket.setsockopt(socket.SOL_IP, socket.IP_TTL, TTL)

    # 2. Call sendOnePing function
    send_time = sendOnePingICMP(traceroute_socket, destination_address, ID)
    # 3. Call receiveOnePing function
    receive_time, icmp_type, code, receive_address = receiveOnePingICMP(traceroute_socket, destination_address, ID, timeout)

    # 4. Close socket
    traceroute_socket.close()

    # 5. Return total network delay
    msg = icmpTypeCodeHandler(icmp_type, code)
    if msg == "TTL equals 0 during transit" or msg == "Echo Reply" or msg == "TTL equals 0 during reassembly":
        delay = (receive_time - send_time) * 1000
        receive_packet_cnt += 1
        if delay < 1:
            print("  <1 ms", end="  ")
        else:
            print("%4d ms" % delay, end="  ")
        return True, receive_address
    else:
        loss_packet_cnt += 1
        print("   *   ", end="  ")
        return False, msg


def doOnePingUDP(destinationAddress, timeout, TTL):
    global loss_packet_cnt, receive_packet_cnt
    udp = socket.getprotobyname("udp")
    icmp = socket.getprotobyname("icmp")
    port = 50000
    try:
        udpSocket=socket.socket(socket.AF_INET, socket.SOCK_DGRAM, udp)
    except :
        print("The socket cannot be created successfully, please try again")
    udpSocket.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, TTL)
    sendTime = time.time()
    udpSocket.sendto("".encode(), (destinationAddress, port))
    udpSocket.close()
    icmpSocket = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp)
    icmpSocket.settimeout(timeout)
    icmpSocket.bind(("", port))
    try:
        data, address = icmpSocket.recvfrom(4096)
        address = address[0]
        receiveTime = time.time()
    except socket.error:
        address = "Request timed out"
        receiveTime = 0

    if receiveTime > 0:
        return_code = True
        receive_packet_cnt += 1
        delay = receiveTime - sendTime
        delay = delay * 1000
        if delay < 1:
            print("  <1 ms", end="  ")
        else:
            print("%4d ms" % delay, end="  ")
    else:
        loss_packet_cnt += 1
        print("   *   ", end="  ")
        return_code = False
    return return_code, address


def doThreePings(destination_address, timeout, protocol, TTL):
    is_successful = False
    return_address = ""
    error_msg = ""

    for i in range(3):
        if(protocol == "icmp"):
            return_code, msg = doOnePingICMP(destination_address, timeout, protocol, TTL)
        else:
            return_code, msg = doOnePingUDP(destination_address, timeout, TTL)
        if return_code:
            return_address = msg
        else:
            error_msg = msg
        is_successful = is_successful | return_code

    if is_successful:
        return return_address
    else:
        return error_msg


def traceroute(host, timeout=1, protocol='icmp'):
    ip_address = socket.gethostbyname(host)
    global loss_packet_cnt
    global receive_packet_cnt
    receive_packet_cnt = 0
    loss_packet_cnt = 0
    packet_cnt = 0
    if ip_address == host:
        print("\nTracing route to %s over a maximum of 30 hops:\n" % host)
    else:
        print("\nTracing route to %s [%s]\nover a maximum of 30 hops:\n" % (host, ip_address))

    for i in range(1, 31):
        packet_cnt += 3
        print("%2d" % i, end='\t')
        return_address = doThreePings(ip_address, timeout, protocol, i)
        try:
            return_host = socket.gethostbyaddr(return_address)[0]
        except Exception as error:
            print(return_address)
            # print(error)
        else:
            print("%s [%s]" % (return_host, return_address))
        if return_address == ip_address:
            break

    print("send = %d, receive = %d, loss = %d(%d%% loss)" %
          (packet_cnt, receive_packet_cnt, loss_packet_cnt, loss_packet_cnt / packet_cnt * 100))
    print("\nTraceroute complete.")


if __name__ == '__main__':
    while True:
        host = input("Please input an IP address: ")
        try:
            timeout = int(input("Please input the timeout: "))
        except Exception as e:
            print("please input an integer")
            continue
        protocol = input("choose the protocol you want (udp or icmp): ")
        if protocol == "icmp" or protocol == "udp":
            break
        else:
            print("please input 'icmp' or 'udp'")

    traceroute(host, timeout, protocol)


    # traceroute("lancaster.ac.uk", 1, "udp")
