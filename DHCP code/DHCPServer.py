import socket
import json
import struct
from datetime import datetime
from threading import Thread, Lock
from socket import socket, AF_INET, SOCK_DGRAM, SOL_SOCKET, SO_REUSEADDR, SO_BROADCAST
import socket as s
from queue import Queue, Empty
import DHCPMessage
import random

""" 
This is DHCP server class.
In this class we handle the operations related to server
This server is implemented multi thread
the server first receives a discovery message and check its xid
then if the xid is new we should add that message to queue
after we receive a discovery message from a client we make thread to manage that client requests"""


class Server(object):

    def __init__(self, ip_address):
        # the port that client sends its message
        self.client_port = 680
        # the port that server receive its message
        self.server_port = 670
        # the maximum bytes that can receive or buffer size
        self.buffer_size = 1024
        # the server ip address
        self.address = ip_address

        # the object of message
        self.message = DHCPMessage.Message("response")

        # load json file
        self.ip_pool, self.lease_time, self.reservation_list, self.black_list = self.configs_loader()
        # the dynamics data. the form of data like this:
        """
        {
            mac1:{
                "Name": ---,
                "IP": ---,
                "ExpireTime": ---
            }
            mac2: ...
        }"""
        self.dynamic_data = {}

        self.queues = {}

        self.client_num = 0

        Thread(target=self.lease_time_checker, args=()).start()

    """this method is the main method of this class.
    it receives the messages and put them in a queue
    the queue is a dictionary. the keys that we use are XIDs"""

    def run(self):
        print("DHCP server is starting...\n\n")
        server_socket = socket(AF_INET, SOCK_DGRAM)
        server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        server_socket.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
        server_socket.bind(('', self.server_port))
        Thread(target=self.show_clients).start()

        while True:

            print("Waiting for incoming message\n")
            message, address = server_socket.recvfrom(self.buffer_size)
            print("the message is received.\n")

            parsed_message = self.message.parseMessage(message)
            xid = parsed_message['XID']
            if xid not in self.queues:
                if parsed_message['option1'][4:6] == b'01':
                    self.queues[xid] = Queue()
                    self.queues[xid].put(parsed_message)
                    Thread(target=self.client_thread, args=(message,)).start()
            else:
                self.queues[xid].put(parsed_message)

    """ this method control the process of sending response to a client
    the server give a thread to each client after its first request. that thread
     run this method."""

    def client_thread(self, message):
        xid, mac = self.discovery_message_parser(message)
        # Open Sender Socket
        with socket(AF_INET, SOCK_DGRAM) as sender_socket:
            destination = ('255.255.255.255', self.client_port)
            sender_socket.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
            # Getting from queue
            try:
                parsed_message = self.queues[xid].get(timeout=120)
            except Empty as e:
                print(e)
                return

            # Checking if mac address is in black list
            mac_address, status, ip_address = self.ip_allocator(parsed_message)
            print("(DHCP discover) is received from client with XID:<<", xid, ">>and MAC:<<", mac_address, ">>\n")
            print("client wih mac:", mac_address, "status:", status, "allocated ip_address:", ip_address)
            if status == "blocked":
                return

            # Send Offer
            offer_message = self.offer_message_maker(xid, mac, ip_address)
            sender_socket.sendto(offer_message, destination)
            print("(DHCP offer) is sent to client with XID:<<", xid, ">> and MAC:<<", mac_address, ">>")

            while True:
                # Getting request from queue
                print("Wait for (DHCP request) of client with XID:<<", xid, ">>and MAC:<<", mac_address, ">>")
                try:
                    parsed_message = self.queues[xid].get(timeout=self.lease_time)
                    if self.ip_to_str_coverter(parsed_message['SIADDR']) != self.address:
                        print("This message doesn't belong to this server. the destination sever is:",
                              self.ip_to_str_coverter(parsed_message['SIADDR']))
                        break
                except Empty as e:
                    print(e)
                    break
                print("(DHCP request) is received from client with XID:<<", xid, ">>and MAC:<<", mac_address, ">>\n")
                ack_message = self.ack_message_maker(xid, mac, ip_address)
                sender_socket.sendto(ack_message, destination)
                print("(DHCP ACK) is sent to client with XID:<<", xid, ">> and MAC:<<", mac_address, ">>\n")

                self.dynamic_data_modifier(ip_address, mac_address)

    """ this method allocate an IP address to the client that requests recently.
    for this job it get mac address and checks the possible states.
    the mac address can be in the : black_list or reservation_list 
    if not we can give an IP address from our pool"""

    def ip_allocator(self, parsed_discovery):
        mac_address = b':'.join((parsed_discovery['CHADDR1'][0:2], parsed_discovery['CHADDR1'][2:4],
                                 parsed_discovery['CHADDR1'][4:6], parsed_discovery['CHADDR1'][6:8],
                                 parsed_discovery['CHADDR2'][0:2], parsed_discovery['CHADDR2'][2:4]))
        mac_address = mac_address.decode()
        for mac in self.black_list:
            if mac == mac_address:
                return mac_address, "blocked", "invalid"

        for mac in self.reservation_list:
            if mac == mac_address:
                return mac_address, "reserved", self.reservation_list[mac]

        for mac in list(self.dynamic_data):
            if mac == mac_address:
                return mac_address, "not expired", self.dynamic_data[mac]["IP"]
        # this is the critical section and so we should use lock
        lock = Lock()
        lock.acquire()
        ip = self.ip_pool.pop()
        lock.release()
        return mac_address, "allocate from pool", ip

    """ this method update the dynamic_data dictionary.
        i.e. after sending the ack we should put the mac address nd IP address 
        and client name and expire time of that IP to this dictionary"""

    def dynamic_data_modifier(self, ip, mac_address):
        # set the expire time
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S").split(":")
        time_to_sec = int(current_time[0]) * 3600 + int(current_time[1]) * 60 + int(current_time[2]) + self.lease_time
        hour = int(time_to_sec / 3600)
        minute = int((time_to_sec - hour * 3600) / 60)
        sec = time_to_sec - (hour * 3600) - (minute * 60)
        expire_time = ':'.join((str(hour), str(minute), str(sec)))
        self.dynamic_data[mac_address] = {
            "Name": ''.join(("Desktop", str(random.randint(0, 10000)))),
            "IP": ip,
            "ExpireTime": expire_time
        }

    """ this method checks if the current time greater than expire time of an IP
        then that IP must be released and add to ip pool"""

    def lease_time_checker(self):
        while 1:
            now = datetime.now()
            currentTime = now.strftime("%H:%M:%S").split(":")
            currentTime_to_sec = int(currentTime[0]) * 3600 + int(currentTime[1]) * 60 + int(currentTime[2])
            if len(self.dynamic_data) != 0:
                for mac in list(self.dynamic_data):
                    expireTime = self.dynamic_data[mac].get("ExpireTime").split(':')
                    expireTime_to_sec = int(expireTime[0]) * 3600 + int(expireTime[1]) * 60 + int(expireTime[2])
                    if currentTime_to_sec >= expireTime_to_sec:
                        address = self.dynamic_data.pop(mac)
                        self.ip_pool.add(address['IP'])

    """ this method parse the discovery message
        it returns the xid and mac address"""

    def discovery_message_parser(self, discovery_message):
        parsed_discovery = self.message.parseMessage(discovery_message)
        xid = parsed_discovery['XID']
        mac = b''.join((parsed_discovery['CHADDR1'], parsed_discovery['CHADDR2']))
        return xid, mac

    """ this method make a offer message for us.
        also it needs the xid and mac address and yiaddr from receiving discovery message
        some fields of base message need to be changed.
        it returns the offer message"""

    def offer_message_maker(self, xid, mac, yiaddr):
        # get the general form of message
        offer_dict = self.message.message_maker()

        # now we should modify some fields
        #    1)modify xid
        offer_dict['XID'] = bytes([int(xid[0:2], 16), int(xid[2:4], 16), int(xid[4:6], 16), int(xid[6:8], 16)])

        #    2)modify yiaddr field
        yiaddr_parts = yiaddr.split('.')
        offer_dict['YIADDR'] = bytes(
            [int(yiaddr_parts[0]), int(yiaddr_parts[1]), int(yiaddr_parts[2]), int(yiaddr_parts[3])])
        #    3)modify siaddr
        siaddr_parts = self.address.split('.')
        offer_dict['SIADDR'] = bytes(
            [int(siaddr_parts[0]), int(siaddr_parts[1]), int(siaddr_parts[2]), int(siaddr_parts[3])])

        #    4)modify mac address
        offer_dict['CHADDR1'] = bytes([int(mac[0:2], 16), int(mac[2:4], 16), int(mac[4:6], 16), int(mac[6:8], 16)])
        offer_dict['CHADDR2'] = bytes(
            [int(mac[8:10], 16), int(mac[10:12], 16), int(mac[12:14], 16), int(mac[14:16], 16)])
        #    5)modify option1
        offer_dict['option1'] = bytes([53, 1, 2, 0])

        # at the end we should join the values of dhcp offer dictionary
        packet = b''.join(offer_dict.values())
        return packet

    """ this method make a ack message for us.
        also it needs the xid and mac address and yiaddr from receiving request message
        some fields of base message need to be changed.
        it returns the ACK message"""

    def ack_message_maker(self, xid, mac, yiaddr):
        # get the general form of message
        ack_dict = self.message.message_maker()

        # now we should modify some fields
        #    1)modify xid
        ack_dict['XID'] = bytes([int(xid[0:2], 16), int(xid[2:4], 16), int(xid[4:6], 16), int(xid[6:8], 16)])

        #    2)modify yiaddr field
        yiaddr_parts = yiaddr.split('.')
        ack_dict['YIADDR'] = bytes(
            [int(yiaddr_parts[0]), int(yiaddr_parts[1]), int(yiaddr_parts[2]), int(yiaddr_parts[3])])

        #    3)modify siaddr
        siaddr_parts = self.address.split('.')
        ack_dict['SIADDR'] = bytes(
            [int(siaddr_parts[0]), int(siaddr_parts[1]), int(siaddr_parts[2]), int(siaddr_parts[3])])

        #    4)modify mac address
        ack_dict['CHADDR1'] = bytes([int(mac[0:2], 16), int(mac[2:4], 16), int(mac[4:6], 16), int(mac[6:8], 16)])
        ack_dict['CHADDR2'] = bytes([int(mac[8:10], 16), int(mac[10:12], 16), int(mac[12:14], 16), int(mac[14:16], 16)])
        #    5)modify option1
        ack_dict['option1'] = bytes([53, 1, 5, 0])
        #    6)modify option2
        ack_dict['option2'] = bytes([51, 1, self.lease_time, 0])
        # at the end we should join the values of dhcp ACK dictionary
        packet = b''.join(ack_dict.values())

        return packet

    """ this method loads the configs.json file
        the fields of json file are saved as some lists"""

    def configs_loader(self):
        with open('configs.json', 'r') as config_file:
            configs = json.load(config_file)

            # create our IP pool
            ip_pool = set()
            if configs['pool_mode'] == 'range':
                ip_range = self.rang(configs['range']['from'], configs['range']['to'])
                for i in ip_range:
                    ip_pool.add(i)
            elif configs['pool_mode'] == 'subnet':
                ip_from, ip_to = self.subnet_to_range(configs['subnet']['ip_block'], configs['subnet']['subnet_mask'])
                ip_range = self.rang(ip_from, ip_to)
                for i in ip_range:
                    ip_pool.add(i)

            lease_time = configs['lease_time']
            reservation_list = configs['reservation_list']
            black_list = configs['black_list']

        return ip_pool, lease_time, reservation_list, black_list

    """ this method get the start and end of an IP range as entries
        and then return the list of IPs"""

    def rang(self, start, end):
        start = struct.unpack('>I', s.inet_aton(start))[0]
        end = struct.unpack('>I', s.inet_aton(end))[0]

        return [s.inet_ntoa(struct.pack('>I', i)) for i in range(start, end)]

    """ this method get the ip_bock and subnet_mask as entries
        and returns the ip_from and ip_to. so then we can gives these outputs
        as entries to range function"""

    def subnet_to_range(self, ip_block, subnet_mask):

        ip_block_parts = ip_block.split('.')
        start = int(ip_block_parts[4]) + 1
        ip_block_parts[4] = str(start)
        ip_from = '.'.join(ip_block_parts)

        subnet_mask_parts = subnet_mask.split('.')
        ip_number = 255 - int(subnet_mask_parts[4])
        ip_block_parts[4] = str(start + ip_number)
        ip_to = '.'.join(ip_block_parts)

        return ip_from, ip_to

    """ this method get an IP address as an entry and then convert 
        it string. the entry in form of byte and the out put is in form of string"""

    def ip_to_str_coverter(self, ip):
        return '.'.join([str(int(ip[i: i + 2].decode(), 16)) for i in range(0, 8, 2)])

    """ this method show MAC Address and IP address and and Expire time and computer name
        of the clients that this server give them IP"""

    def show_clients(self):
        while True:
            user_input = input()
            if user_input.startswith('s'):
                print("The list of clients that has IP:\n")
                print(self.dynamic_data)


if __name__ == '__main__':
    # the IP of first server
    dhcp_server = Server('192.168.10.1')

    # the IP of second server
    # dhcp_server = Server('192.168.10.2')

    dhcp_server.run()
