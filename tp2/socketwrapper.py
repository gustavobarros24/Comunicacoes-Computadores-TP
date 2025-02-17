from random import randint
from socket import socket, AF_INET, SOCK_DGRAM, timeout
from datagram import Datagram, Flags
from time import sleep

SOCK_TIMEOUT = 5
SOCK_MAX_RETRIES = 3

class SocketWrapper:

    def __init__(self, local_addr, local_port=None, starting_seqnr=None, starting_acknr=0):
        self.local_addr = local_addr
        self.local_port = local_port
        self.sock = socket(AF_INET, SOCK_DGRAM)
        self.sock.bind((local_addr, local_port))
        self.seqnr = starting_seqnr if starting_seqnr != None else randint(1000,8000)
        self.acknr = starting_acknr

    #################################################################################################

    def send(self, dest_addr, dest_port, flags: Flags, payload=None, acknr=None):
        
        datagram = Datagram(
            origin_addr=self.local_addr,
            origin_port=self.local_port,
            dest_addr=dest_addr,
            dest_port=dest_port,
            flags=flags,
            seqnr=self.seqnr,
            acknr=acknr if acknr is not None else self.acknr,
            payload=payload,
        )
        self.sock.sendto(datagram.serialize(), (dest_addr, dest_port))
        self.sockprint(f"Sent {datagram}")
        return datagram

    def send_and_wait_ack(self, dest_addr, dest_port, flags, payload=b'', acknr=None) -> Datagram:

        for i in range(SOCK_MAX_RETRIES):

            # We pass a specific acknr in a synack situation. Every other case uses the self-stored acknr.
            sent_datagram = self.send(dest_addr, dest_port, flags, payload, acknr=self.acknr if acknr is None else acknr)
            response, _ = self.receive()

            if response and response.flags.ack and response.acknr == (sent_datagram.seqnr+sent_datagram.payload_size()+1):
                #self.sockprint("ACK received")
                self.seqnr += sent_datagram.payload_size()+1
                return response
            else:
                self.acknr -= response.seqnr+response.payload_size()+1
                self.sockprint("ACK not received, resending...")
                sleep(2**i) # exponentially sleep more between retransmissions
        
        if i == SOCK_MAX_RETRIES:
            raise TimeoutError("Maximum retransmission attempts reached.")

    def send_ack(self, received: Datagram):
        
        def newflags(flags: Flags) -> Flags:
            if flags == Flags(True, False, False): return Flags(True, True, False)   # if syn return synack
            elif flags == Flags(False, False, True): return Flags(False, True, True) # if fin return finack
            else: return Flags(False, True, False)                                   # if anything else, return a normal ack

        send_method = (
            self.send_and_wait_ack 
            if received.is_syn() or received.is_fin() 
            else self.send
        )

        send_method(
            dest_addr=received.origin.addr,
            dest_port=received.origin.port,
            flags=newflags(received.flags),
            payload=b"",
            acknr=received.seqnr + received.payload_size()+1,
        )

    #################################################################################################

    def receive(self, with_timeout=False) -> tuple[Datagram, str]:
        
        if with_timeout:
            self.sock.settimeout(SOCK_TIMEOUT)

        try:
            data, addr = self.sock.recvfrom(1024)
            #sleep(1)
            datagram = Datagram.deserialize(data)
            self.sockprint(f"Recv {datagram}")
            self.acknr = datagram.seqnr+datagram.payload_size()+1

            self.sock.settimeout(None)
            return datagram, addr
        
        except TimeoutError:
            self.sockprint("Recv timeout")
            self.sock.settimeout(None)
            return None, None

    def receive_and_ack(self, with_timeout=False) -> tuple[Datagram, str]:
        
        if with_timeout:
            self.sock.settimeout(SOCK_TIMEOUT)

        try:
            data, addr = self.sock.recvfrom(1024)
            #sleep(1)
            datagram = Datagram.deserialize(data)
            self.sockprint(f"Recv {datagram}")
            self.acknr = datagram.seqnr+datagram.payload_size()+1

            self.sock.settimeout(None)
            self.send_ack(datagram)
            return datagram, addr
        
        except TimeoutError:
            self.sockprint("Recv timeout")
            self.sock.settimeout(None)
            return None, None

    #################################################################################################

    def close(self):
        self.sock.close()

    #################################################################################################

    def sockprint(self, string, deviceID=None):

        # deviceID is an argument that's only useful when using sockprint from a Server_Worker instance.
        port = f"{self.local_port}"
        if deviceID is not None:
            print(f"({port}-{deviceID}) {string}")
        else:
            print(f"({port}) {string}")



    