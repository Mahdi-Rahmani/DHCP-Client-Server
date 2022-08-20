import threading
from socket import *
import random
import time
import DHCPMessage
import binascii

""" 
This is DHCP client class.
In this class we handle the operations related to client
the client first sends a discovery as a broad cast message.
then after receiving offer from server it should create the request message 
end of all if the server send the ack message the IP is allocated to this client.
the client every lease/2 time just sends request message to extend its expire time  """


class Client:
    """ The constructor of this class.
    It gets a Mac address related to this class as an entry.
    the fields of this class is defined also"""

    def __init__(self, MAC_Addrress):
        # the port that client sends its message
        self.client_port = 680
        # the port that server receive its message
        self.server_port = 670
        # the maximum bytes that can receive or buffer size
        self.buffer_size = 1024

        # first interval for waiting
        self.initial_interval = 10
        # maximum time of waiting
        self.backoff_cutoff = 120
        # after timeout time if the server doesnt send ack we should send discover message again
        self.timeout = 5

        # the client mac address is assigned to it when it is created
        self.Mac_Address = MAC_Addrress
        # the XID
        self.xid = []

        # the message object
        self.message = DHCPMessage.Message("request")

    """ this method run the client.
    the client for getting an IP address from DHCP server should do some processes.
    the processes is done here step by step. some steps need a specific time to get message
    if it doesnt happen , time out is occur and we should do some related works"""

    def run(self):
        print("DHCP client with mac address(", self.maclist_to_str(self.Mac_Address), ") is starting...\n")
        # The UDP socket is created
        with socket(AF_INET, SOCK_DGRAM) as client_socket:
            client_socket.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
            client_socket.bind(('0.0.0.0', self.client_port))
            destination = ('<broadcast>', self.server_port)

            # the process of getting an IP address
            while True:
                # the first part:
                #    1) sending discovery
                #    2) parsed the receiving offer message
                try:
                    discovery_message = self.discover_message_maker()
                    client_socket.sendto(discovery_message, destination)
                    print("The discover message was sent")

                    # now we should receive the offer message
                    yiaddr, siaddr = self.offer_message_receiver(client_socket)
                    print("the offer message was received")

                except timeout:
                    new_waiting = self.initial_interval + self.initial_interval * 2 * random.random()
                    if new_waiting < self.backoff_cutoff:
                        self.initial_interval = new_waiting
                    else:
                        self.initial_interval = self.backoff_cutoff
                    print("time out is occurred in sending discovery")

                    continue

                # the second part:
                #    1) sending request
                #    2) parsed the receiving ACK message
                # extend its expire time after getting IP
                try:
                    while True:
                        request_message = self.request_message_maker(yiaddr, siaddr)
                        client_socket.sendto(request_message, destination)
                        print("the request message is sent")

                        # Setting acknowledgement timeout
                        client_socket.settimeout(self.timeout)

                        # now we should receive the ACk message
                        your_ip, lease_time = self.ack_message_receiver(client_socket)
                        print("the ACK message is received")
                        # now we should print the ip
                        print("the client IP address is: ", your_ip, "\n")
                        time.sleep(lease_time / 2)
                except timeout:
                    print("the ack message isn't received in time out time\n")
                    continue

    """ this method make a discover message for us.
    some fields of base message need to be changed.
    it returns the discover message"""

    def discover_message_maker(self):
        # first we should generate a specific xid
        self.xid = self.xid_generator()

        # then we should get the general form of message
        dhcp_discover_dict = self.message.message_maker()
        dhcp_discover_dict['XID'] = bytes(self.xid)
        mac = bytes(self.Mac_Address)
        dhcp_discover_dict['CHADDR1'] = bytes([mac[0], mac[1], mac[2], mac[3]])
        dhcp_discover_dict['CHADDR2'] = bytes([mac[4], mac[5], 0, 0])
        dhcp_discover_dict['option1'] = bytes([53, 1, 1, 0])

        # at the end we should hexlify the values of dhcp discover dictionary
        packet = b''.join(dhcp_discover_dict.values())
        return packet

    """ this method make a request message for us.
        also it needs the YIAddr and SIAddr from receiving offer message
        some fields of base message need to be changed.
        it returns the request message"""

    def request_message_maker(self, yiaddr, siaddr):
        # get the general form of the message
        dhcp_request_dict = self.message.message_maker()

        # now we should modify some fields
        dhcp_request_dict['XID'] = bytes(self.xid)
        yiaddr = b''.join(yiaddr)
        siaddr = b''.join(siaddr)
        dhcp_request_dict['CIADDR'] = bytes(
            [int(yiaddr[0:2], 16), int(yiaddr[2:4], 16), int(yiaddr[4:6], 16), int(yiaddr[6:8], 16)])
        dhcp_request_dict['SIADDR'] = bytes(
            [int(siaddr[0:2], 16), int(siaddr[2:4], 16), int(siaddr[4:6], 16), int(siaddr[6:8], 16)])
        mac = bytes(self.Mac_Address)
        dhcp_request_dict['CHADDR1'] = bytes([mac[0], mac[1], mac[2], mac[3]])
        dhcp_request_dict['CHADDR2'] = bytes([mac[4], mac[5], 0, 0])
        dhcp_request_dict['option1'] = bytes([53, 1, 3, 0])
        # at the end we should hexlify the values of dhcp request dictionary
        packet = b''.join(dhcp_request_dict.values())
        return packet

    """ this method receive the offer message from socket.
        because the server broadcast the messages so we should check 
        if the received message belongs to us or doesn't."""

    def offer_message_receiver(self, client_socket):
        # set timeout of socket
        client_socket.settimeout(self.initial_interval)
        while True:
            offer_message, address = client_socket.recvfrom(self.buffer_size)
            yiaddr, siaddr, xid, message_type = self.offer_message_parser(offer_message)
            if xid == binascii.hexlify(bytes(self.xid)) and message_type[4:6] == b'02':
                return yiaddr, siaddr

    """ this method receive the offer message from socket.
       because the server broadcast the messages so we should check 
       if the received message belongs to us or doesn't."""

    def ack_message_receiver(self, client_socket):
        # set timeout of socket
        client_socket.settimeout(self.timeout)
        while True:
            ack_message, address = client_socket.recvfrom(self.buffer_size)
            my_ip, lease_time, xid, message_type = self.ack_message_parser(ack_message)
            if xid == binascii.hexlify(bytes(self.xid)) and message_type[4:6] == b'05':
                return my_ip, lease_time

    """ this method parse the offer message for us.
        we need the information of yiaddr and siaddr fields
        it returns yiaddr and siaddr"""

    def offer_message_parser(self, offer_message):
        parsed_offer = self.message.parseMessage(offer_message)
        # find xid
        xid = parsed_offer['XID']

        # find your IP address
        yiaddr = [parsed_offer['YIADDR'][0:2], parsed_offer['YIADDR'][2:4], parsed_offer['YIADDR'][4:6],
                  parsed_offer['YIADDR'][6:8]]

        # find server IP address
        siaddr = [parsed_offer['SIADDR'][0:2], parsed_offer['SIADDR'][2:4], parsed_offer['SIADDR'][4:6],
                  parsed_offer['SIADDR'][6:8]]

        # find the type of message
        message_type = parsed_offer['option1']

        return yiaddr, siaddr, xid, message_type

    """ this method parse the ack message for us.
        we need the information of yiaddr and option2 fields
        it returns the IP address and lease time"""

    def ack_message_parser(self, ack_message):
        parsed_ack = self.message.parseMessage(ack_message)
        # find xid
        xid = parsed_ack['XID']

        # find your ip address from message
        yiaddr = [parsed_ack['YIADDR'][0:2], parsed_ack['YIADDR'][2:4], parsed_ack['YIADDR'][4:6],
                  parsed_ack['YIADDR'][6:8]]

        # create the the IP for printing
        myIP = '.'.join(
            (str(int(yiaddr[0], 16)), str(int(yiaddr[1], 16)), str(int(yiaddr[2], 16)), str(int(yiaddr[3], 16))))

        # find the type of message
        message_type = parsed_ack['option1']

        # find the lease time
        lease_time = int(parsed_ack['option2'][4:6], 16)

        return myIP, lease_time, xid, message_type

    """ this method generate a random xid"""

    def xid_generator(self):
        xid_4bytes = []
        for i in range(4):
            xid_4bytes.append(random.randint(0, 255))
        return xid_4bytes

    """ this method convert the list of hex parts of a mac address to one string"""

    def maclist_to_str(self, mac_list):
        mac = binascii.hexlify(bytes(mac_list)).decode()
        mac_str = ""
        for i in range(0, 10, 2):
            mac_str = mac_str + mac[i:i + 2] + ":"
        mac_str = mac_str + mac[10:12]
        return mac_str


if __name__ == '__main__':
    # sample of block mac address
    # mac_address = [0xff, 0xc1, 0x9a, 0xd6, 0x4d, 0xcc]

    # sample of reserved mac address
    # mac_address = [0xff, 0xc1, 0x9a, 0xd6, 0x4d, 0xaa]

    # sample of client without any limitations
    mac_address = [0xff, 0xc1, 0x9a, 0xd6, 0x4d, 0x05]

    client = Client(mac_address)
    client.run()
