# DHCP  
This projetct is the third project of Computer Networks course at AUT. It has two parts. First we should answer to some questions related to the project and then implement Ir according to the [project explanation.](https://github.com/Mahdi-Rahmani/DHCP-Client-Server/blob/main/Project%20Explanation/CN-P-3.pdf)  
  
## Questions  
In this part we have some questions to answer. They are written below:  
 1. Describe the uses, advantages and disadvantages of the DHCP protocol.  
 2. Draw the format of DHCP packets and explain the use and function of each field. (You can get help from [RFC 2131](https://datatracker.ietf.org/doc/html/rfc2131))  
 3. Explain how to exchange messages in the DHCP protocol with a diagram and fully explain each step.  
 4. What ports do DHCP Client and DHCP Server use?  
  4.1. Why does the client use a specific port?  
  4.2. Why is the assignment of the address to the client not terminated in the second step?  
  4.3. What is the meaning of receiving confirmation from the server at the last stage?  
 5. Briefly explain what MAC Address is?  
The answer file is added in [Question answer](https://github.com/Mahdi-Rahmani/DHCP-Client-Server/blob/main/Question%20answer/Questions%20answer.pdf)  
  
## Implementation  
### step1) Client  
The client runs and sends Discovery and waits for the Offer to be received from the server. After receiving the Offer, it sends the Request message and waits for the Ack to arrive. After receiving the Ack, you must print the received IP in the terminal.
Implementation details to consider:
* DHCPDiscover and DHCPRequest requests must be implemented in the client.
* If Ack does not arrive after a certain timeout, the client must restart the process by sending a DISCOVER message. Consider Timeout in the client as an arbitrary value in the code.
* The DISCOVER message itself has a timer and works in such a way that if a certain period of time has passed since the previous DISCOVER message was sent, it checks whether we have received an IP or not, if we have not received it or we had received it but it had expired, the DISCOVER message will be sent again. will be sent How to calculate the waiting time for this scheduler is as follows: (Note: This scheduler is always working.)
  * On the client side, two constants with the letters cutoff-backoff and interval-initial are kept with default values of 120 and 10 respectively, both of which are in seconds.
  * After sending the first DISCOVER message, this scheduler starts working and waits for the interval-initial time, and as mentioned before, it sends DISCOVER again if needed.
  * After sending the second DISCOVER, it does not wait as long as interval-initial, but after sending DISCOVER again, this interval is calculated with this formula: R*2*P, where R is a random number between 0 and 1 and P stands for Previous interval, that is The amount of time it has waited before.
  * This interval increase for the waiting period goes up to the cutoff-backoff limit, and if it exceeds this, it is set to the same value.
  
### step2) Server  
The server runs and is always ready to receive Discovery. When Discovery is received on the server, it sends the Offer and then waits to receive the Request. After receiving the request, it sends an Ack message.
Implementation details to consider:
* DHCPOffer and DHCPAck must be implemented on the server.
* The server must be multi-threaded, that is, after receiving Discovery, it should continue the other steps for each separate client and be ready to receive Discovery messages continuously.
* The server has an IP Pool that assigns IPs from free IPs in this pool. If the IP is used by a client and was previously assigned, it should not be assigned to another client. (Duplicate IP should not be assigned.)
* The server must consider the Lease time for each client, and after this time, return the IP to the Pool, and then the IP will be among the free IPs.
* Also, if an IP was previously assigned to a MAC Address, if an IP request comes from the same MAC Address again, a new IP should not be assigned to it, and only the old IP that has not passed its Lease Time will be re-sent and Lease Its time is renewed. (Of course, if the lease time has passed, there is no problem and a new IP can be assigned.)
* The server must be able to reserve IP for specific MAC addresses. (One IP for each MAC Address). That is, in a way, we consider static IP for certain devices. When an IP is reserved, it will not be given to any other client, even if the client for whom this IP is reserved is offline at that moment.
* Like booking, we also have the ability to block specific MAC addresses. In this way, if we had a request for IP from specific MACs, we will not respond to the request.
* The server must keep the device name, the remaining time until the expiration of that IP and the assigned IP itself for each MAC Address assigned to that IP, and by writing the command clients_show in the console, in each line Expire Time, IP Address, Mac Address, Computer name are displayed in order.  
* When the server wants to run, values such as IP Pool interval, Lease time, etc. must be read from a configs.json file.  
