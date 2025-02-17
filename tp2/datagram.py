from collections import namedtuple
from random import randint
from msgpack import packb, unpackb
from zlib_ng.zlib_ng import compress, decompress


Flags = namedtuple('Flags', 'syn ack fin')
Location = namedtuple('Location', 'addr port')

class Datagram:

    def __init__(
            self,
            origin_addr, origin_port,
            dest_addr, dest_port,
            flags: Flags,
            seqnr: int,
            acknr: int,
            payload: bytes = b''
        ):

        self.origin: Location = Location(addr=origin_addr, port=origin_port)
        self.dest: Location = Location(addr=dest_addr, port=dest_port)

        self.flags: Flags = flags
        self.seqnr: int = seqnr
        self.acknr: int = acknr
        self.payload: bytes = payload

    def __str__(self):
        
        def bin(boolean):
            return 1 if boolean else 0

        flags_str = f"s{bin(self.flags.syn)}a{bin(self.flags.ack)}f{bin(self.flags.fin)}"
        finalstr = f"[Dgram {self.origin.port}->{self.dest.port}] {flags_str} - SeqNr{self.seqnr} AckNr{self.acknr} - Payload {self.payload_size()} B"
        return finalstr

    #####################################################################################################

    def payload_size(self):
        return len(self.payload) if self.payload is not None else 0

    #####################################################################################################
    
    def serialize(self):
            
        def to_dict(self):
            
            flags = [
                self.flags.syn,
                self.flags.ack,
                self.flags.fin
            ]

            d = {
                'o': [self.origin.addr, self.origin.port],
                'd': [self.dest.addr, self.dest.port],
                'f': flags,
                's': self.seqnr,
                'a': self.acknr,
                'p': self.payload or b''
            }

            #for k,v in d.items():
            #    print(type(v), v)

            return d    

        return compress(packb(to_dict(self), use_bin_type=True, strict_types=True))

    @classmethod
    def deserialize(cls, data: bytes):
        # Decompress and unpack the data
        unpacked_data = unpackb(decompress(data))

        # Recreate the Flags namedtuple from the unpacked dictionary
        flags = Flags(
            unpacked_data['f'][0],
            unpacked_data['f'][1],
            unpacked_data['f'][2]
            )

        # Create a new Datagram object with the unpacked data
        return cls(
            unpacked_data['o'][0], unpacked_data['o'][1],
            unpacked_data['d'][0], unpacked_data['d'][1],
            flags,
            unpacked_data['s'],
            unpacked_data['a'],
            unpacked_data['p']
            )

    #####################################################################################################

    def is_syn(self):
        return self.flags.syn == True and self.flags.ack == False
    
    def is_synack(self):
        return self.flags.syn == True and self.flags.ack == True

    def is_fin(self):
        return self.flags.fin == True and self.flags.ack == False
    
    def is_finack(self):
        return self.flags.fin == True and self.flags.ack == True
    



