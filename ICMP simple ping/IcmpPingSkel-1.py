import os 
import argparse 
import socket
import struct
import select
import time

#Kollen Gruizenga
#CSCI 340 Networking
#icmp pinger skeleton class


ICMP_ECHO_REQUEST = 8 # (Platform specific)
DEFAULT_TIMEOUT = 2
DEFAULT_COUNT = 4 


class Pinger(object):
    " Pings a specified host  "
    
    def __init__(self, target_host, count=DEFAULT_COUNT, timeout=DEFAULT_TIMEOUT):
        self.target_host = target_host
        self.count = count
        self.timeout = timeout


    def do_checksum(self, source_string):
        "  Verify the packet integrity by calculating the checksum "
        sum = 0
        max_count = (len(source_string)/2)*2
        count = 0
        while count < max_count:

            # for Python 2.7.x :
            # val = ord(source_string[count + 1])*256 + ord(source_string[
            val = source_string[count + 1]*256 + source_string[count]
            # In Python 3, indexing a bytes object returns an integer, so ord() is redundant.

            sum = sum + val
            sum = sum & 0xffffffff 
            count = count + 2
     
        if max_count<len(source_string):
            sum = sum + ord(source_string[len(source_string) - 1])
            sum = sum & 0xffffffff 
     
        sum = (sum >> 16)  +  (sum & 0xffff)
        sum = sum + (sum >> 16)
        answer = ~sum
        answer = answer & 0xffff
        answer = answer >> 8 | (answer << 8 & 0xff00)
        return answer
 
    def receive_pong(self, sock, ID, timeout):
        """
        We have to create a socket on our side so we can receive the replies from the destination host.
        We also have to make sure not to wait too long “TIMEOUT”.
        """
        time_remaining = timeout
        while True: #find timeout
            start_time = time.time()
            readable = select.select([sock], [], [], time_remaining)
            time_spent = (time.time() - start_time)
            if readable[0] == []: #Timeout (occurs if readable is 0)
                return
     
            time_received = time.time()
            recv_packet, addr = sock.recvfrom(1024)
            icmp_header = recv_packet[20:28]
            #The bbHHh is the byte format used to unpack the icmp_header into the various variable components
            type, code, checksum, packet_ID, sequence = struct.unpack(
                "bbHHh", icmp_header)
            if packet_ID == ID:
                bytes_In_double = struct.calcsize("d")
                time_sent = struct.unpack("d", recv_packet[28:28 + bytes_In_double])[0]
                return time_received - time_sent
     
            time_remaining = time_remaining - time_spent
            if time_remaining <= 0:
                return
     
     
    def send_ping(self, sock,  ID):
        """
        We have to create a packet and send it to the destination host,
        we are creating a dummy ICMP packet and attaching it to the IP header. 
        """
        target_addr  =  socket.gethostbyname(self.target_host)
     
        my_checksum = 0
     
        # Create a dummy header with a 0 checksum.
        header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, my_checksum, ID, 1)
        bytes_In_double = struct.calcsize("d")
        data = (192 - bytes_In_double) * "Q"
        data = struct.pack("d", time.time()) + bytes(data.encode('utf-8'))
     
        # Get the checksum on the data and the dummy header.
        my_checksum = self.do_checksum(header + data)
        header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, socket.htons(my_checksum), ID, 1)
        
        #add the data from above to the header to create a complete packet
        packet = header + data
        #send the packet to the target address
        sock.sendto(packet, (target_addr, 1))
     
     
    def ping_once(self):
        """
        Returns the delay (in seconds) or none on timeout.
        """
        icmp = socket.getprotobyname("icmp")
        try:
        #add the ipv4 socket (same as we did in our first project, SOCK_RAW(to bypass some of the TCP/IP handling by your OS) 
	#and the ICMP packet
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp)
        except socket.error as e:
            if e.errno == 1:
                # print a message if not run by superuser/admin, so operation is not permitted
                e.msg +=  "ICMP messages must be sent from root user usage"
                raise socket.error(e.msg)
        except Exception as e:
            #print the errror message    
            print ("Exception: %s" %(e))
    
        my_ID = os.getpid() & 0xFFFF
        
        #Call the definition from send.ping above and send to the socket you created above
        self.send_ping(sock, my_ID)
        delay = self.receive_pong(sock, my_ID, self.timeout)
        sock.close()
        return delay
     
     
    def ping(self):
        " Run the ping process "
        for i in range(self.count):
            print ("Ping to %s..." % self.target_host,)
            try:
                delay  =  self.ping_once()
            except socket.gaierror as e:#if ping failed due to socket error
                print ("Ping failed. (socket error: '%s')" % e[1])
                break
     
            if delay  ==  None:#if ping failed due to timeout
                print ("Ping failed. (timeout within %ssec.)" % self.timeout)
            else:
                delay  =  delay * 1000
                print ("Get pong in %0.4fms" % delay)

 
 
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Python ping')
    parser.add_argument('--target-host', action="store", dest="target_host", required=True)
    given_args = parser.parse_args()  
    target_host = given_args.target_host
    pinger = Pinger(target_host=target_host)
    pinger.ping()
