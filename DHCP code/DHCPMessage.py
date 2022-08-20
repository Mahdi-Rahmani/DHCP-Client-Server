import binascii

"""
    in this class we handle the operations related to message
    the format of dhcp messages like this:
        0           7           15         23          31
        +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
        |OP code(op)|  htype    |  hlen     |   hops    |
        +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
        |           Transaction ID (xid)                |
        +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
        |     Seconds(sec)      |     Flags(flags)      |
        +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
        |        Client IP Address(ciaddr)              |
        +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
        |         Your IP Address(yiaddr)               |
        +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
        |         Server IP Address(siaddr)             |
        +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
        |         Gateway IP Address(giaddr)            |
        +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
        |    Client Hardware Address(chaddr) (16bytes)  |
        +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
        |         Server Name(sname) (64bytes)          |
        +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
        |         Boot File Name(bname) (128bytes)      |
        +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
        | mcookie   | Options(options) (up to 214 bytes)|
        +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+"""


class Message:
    def __init__(self, message_type):

        # the opcode is achieved from message type
        if message_type == "request":
            self.opcode = [0x01]
        if message_type == "response":
            self.opcode = [0x02]

        # the hardware type is ethernet
        self.hardware_type = [0x01]

        # the mac address is 6 bytes
        self.hardware_address_length = [0x06]

        # this 192 byte is unused in this project
        self.server_name, self.boot_file_name = self.sname_bname_create()

    """ this method create the sname and bname fields of the message
    this fields in this project aren't used and must be 0"""

    def sname_bname_create(self):
        sname = []
        bname = []
        for i in range(192):
            if i < 64:
                sname.append(0)
            else:
                bname.append(0)
        return sname, bname

    """ this method create the form of the message 
    in each message like : discovery, offer and etc. some filds are changed only"""

    def message_maker(self):
        message = {'OP': bytes([0x01]),
                   'HTYPE': bytes([0x01]),
                   'HLEN': bytes([0x06]),
                   'HOPS': bytes([0x00]),
                   'XID': bytes([0x00, 0x00, 0x00, 0x00]),
                   'SECS': bytes([0x00, 0x00]),
                   'FLAGS': bytes([0x00, 0x00]),
                   'CIADDR': bytes([0x00, 0x00, 0x00, 0x00]),
                   'YIADDR': bytes([0x00, 0x00, 0x00, 0x00]),
                   'SIADDR': bytes([0x00, 0x00, 0x00, 0x00]),
                   'GIADDR': bytes([0x00, 0x00, 0x00, 0x00]),
                   'CHADDR1': bytes([0x00, 0x00, 0x00, 0x00]),
                   'CHADDR2': bytes([0x00, 0x00, 0x00, 0x00]),
                   'CHADDR3': bytes([0x00, 0x00, 0x00, 0x00]),
                   'CHADDR4': bytes([0x00, 0x00, 0x00, 0x00]),
                   'MCookie': bytes([0x00, 0x00, 0x00, 0x00]),
                   'SName': bytes(self.server_name),
                   'BName': bytes(self.boot_file_name),
                   'option1': bytes([0, 0, 0, 0]),
                   'option2': bytes([0, 0, 0, 0])}
        return message

    """this method can parse the dhcp message
    it gives us the dictionary form of receiving message"""

    def parseMessage(self, response):
        message = binascii.hexlify(response)
        parsed_message = {'OP': message[0:2],
                          'HTYPE': message[2:4],
                          'HLEN': message[4:6],
                          'HOPS': message[6:8],
                          'XID': message[8:16],
                          'SECS': message[16:20],
                          'FLAGS': message[20:24],
                          'CIADDR': message[24:32],
                          'YIADDR': message[32:40],
                          'SIADDR': message[40:48],
                          'GIADDR': message[48:56],
                          'CHADDR1': message[56:64],
                          'CHADDR2': message[64:72],
                          'CHADDR3': message[72:80],
                          'CHADDR4': message[80:88],
                          'SName': message[88:216],
                          'BName': message[216:472],
                          'MCookie': message[472:480],
                          'option1': message[480:488],
                          'option2': message[488:496]}
        return parsed_message
