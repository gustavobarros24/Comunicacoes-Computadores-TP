from utils import Colours
from nettask_task import NetTask_Task
from nettask_report import NetTask_Report

from typing import Dict, List

from msgpack import packb, unpackb
from zlib_ng.zlib_ng import compress, decompress


nettask_message_tags = {
    't' : 'NT payload has NetTask_Task',
    'f' : 'NT payload has the final NetTask_Task to be sent',
    'r' : 'NT payload has NetTask_Report',
    'c' : 'NT payload is empty, message sent for deviceID recon'
}


class NetTask_Message:

    def __init__(self, author:str, tag:str, payload: bytes=b''):
        self.author = author
        self.tag = tag
        self.payload = payload

    def __str__(self):
        return "\n".join([
            f"[NetTask Message]",
            f" | Tag: {nettask_message_tags[self.tag]}"
        ])

    ##############################################################################

    # Returns a tuple that indicates (contains task, is final task)
    def contains_task(self) -> tuple[bool,bool]:
        if self.tag in {'t', 'f'}:
            try:
                NetTask_Task.deserialize(self.payload)
                return (True, self.tag=='f')
            except: pass
        return False

    def contains_report(self) -> bool:
        if self.tag == 'r':
            try:
                NetTask_Report.deserialize(self.payload)
                return True
            except: pass
        return False

    def contains_only_header(self) -> bool:
        return self.tag == 'c'

    ##############################################################################

    def payload_size(self):
        return len(self.payload)

    ##############################################################################

    def serialize(self):
        return compress(packb({
            'a': self.author,
            't': self.tag,
            'p': self.payload
        }, use_bin_type=True, strict_types=True))

    @classmethod
    def deserialize(cls, data: bytes):
            unpacked_data = unpackb(decompress(data))
            return cls(
                author=unpacked_data['a'],
                tag=unpacked_data['t'],
                payload=unpacked_data['p']
            )
    





