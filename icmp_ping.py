from socket import *
import os
import sys
import struct
import time
import select
import binascii
import statistics

ICMP_ECHO_REQUEST = 8

def checksum(string):
    csum = 0
    countTo = (len(string) // 2) * 2
    count = 0

    while count < countTo:
        thisVal = (string[count + 1]) * 256 + (string[count])
        csum += thisVal
        csum &= 0xffffffff
        count += 2

    if countTo < len(string):
        csum += (string[len(string) - 1])
        csum &= 0xffffffff

    csum = (csum >> 16) + (csum & 0xffff)
    csum = csum + (csum >> 16)
    answer = ~csum
    answer = answer & 0xffff
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer

def receiveOnePing(mySocket, ID, timeout, destAddr):
    timeLeft = timeout

    while 1:
        startedSelect = time.time()
        whatReady = select.select([mySocket], [], [], timeLeft)
        howLongInSelect = (time.time() - startedSelect)
        if whatReady[0] == []: # Timeout
            return "Request timed out."
        
        timeReceived = time.time()
        recPacket, addr = mySocket.recvfrom(1024)

        #Fetch the ICMP header from the IP packet
        Header_ICMP = recPacket[20:28]
        type_ICMP, code_ICMP, checksum_ICMP, packetID_ICMP, sequence_ICMP = struct.unpack('bbHHh', Header_ICMP)
        if packetID_ICMP == ID:
            bytes_ICMP = struct.calcsize('d')
            timeStamps = struct.unpack('d', recPacket[28:28 + bytes_ICMP])
            time_of_sent_ICMP = timeStamps[0]
            return timeReceived - time_of_sent_ICMP

        timeLeft = timeLeft - howLongInSelect
        if timeLeft <= 0:
            return "Request timed out."
        
def sendOnePing(mySocket, destAddr, ID):
    # Header is type (8), code (8), checksum (16), id (16), sequence (16)

    myChecksum = 0

    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    data = struct.pack("d", time.time())
    # Calculate the checksum on the data and the dummy header.
    myChecksum = checksum(header + data)

    # Get the right checksum, and put in the header
    if sys.platform == 'darwin':
        # Convert 16-bit integers from host to network byte order
        myChecksum = htons(myChecksum) & 0xffff
    else:
        myChecksum = htons(myChecksum)

    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    packet = header + data

    mySocket.sendto(packet, (destAddr, 1)) # AF_INET address must be tuple, not str
    # Both LISTS and TUPLES consist of a number of objects
    # which can be referenced by their position number within the object.

def doOnePing(destAddr, timeout):
    icmp = getprotobyname("icmp")
    # SOCK_RAW is a powerful socket type. For more details: http://sock-raw.org/papers/sock_raw

    mySocket = socket(AF_INET, SOCK_RAW, icmp)

    myID = os.getpid() & 0xFFFF # Return the current process i
    sendOnePing(mySocket, destAddr, myID)
    delay = receiveOnePing(mySocket, myID, timeout, destAddr)
    mySocket.close()
    return delay

def ping(host, timeout=1):
    packet_min = float('inf')  # Initialize with a large value
    packet_max = 0
    timeRTT = []  # List to store round-trip times
    packageRev = 0
    packageSent = 0

    try:
        dest = gethostbyname(host)
    except gaierror as e:
        print(f"Pinging {host} using Python:")
        print("\nRequest timed out.\nRequest timed out.\nRequest timed out.\nRequest timed out.")
        print("\n--- " + host + " ping statistics ---")
        print("4 packets transmitted, 0 packets received, 100.0% packet loss")
        print("round-trip min/avg/max/stddev = 0/0.0/0/0.0 ms")
        return [0, 0, 0, 0]

    print("Pinging " + dest + " using Python:")
    print("")

    for i in range(0, 4):
        delay = doOnePing(dest, timeout)

        if isinstance(delay, str):
            print(delay)
        else:
            packageSent += 1
            timeRTT.append(delay)
            packageRev += 1

            packet_min = min(packet_min, delay)
            packet_max = max(packet_max, delay)

            # Display round-trip time for successful ping
            print(f"Reply from {dest}: bytes=36 time={delay * 1000:.2f}ms TTL=117")

        time.sleep(1)

    if packageRev > 0:  # Check if there are successful replies before calculating statistics
        packet_avg = statistics.mean(timeRTT) * 1000  # Convert to milliseconds
        pstdev_var = statistics.pstdev(timeRTT)

        print("\n=== " + host + " Ping ===")
        print(f"{packageSent} - packets transmitted\n{packageRev} - packets received\n"
              f"{100.0 * (packageSent - packageRev) / packageSent:.1f}% - packet loss")
        print(f"{packet_min * 1000:.2f}/{packet_avg:.2f}/{packet_max * 1000:.2f}/{pstdev_var:.2f} ms")
    else:
        print("\n=== " + host + " Ping ===")
        print(f"{packageSent} - packets transmitted\n{packageRev} - packets received\n100.0% - packet loss")
        print("0/0.0/0/0.0 ms")


if(len(sys.argv) > 1):
    ping(sys.argv[1])
else:
    print("Please enter arguments \nex. ping google.com")