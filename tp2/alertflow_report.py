from enum import Enum
from msgpack import packb, unpackb
from zlib import compress, decompress

from utils import Colours

class TypeUtilities(Enum):
    @classmethod
    def corresponds(cls, value: str):
        for item in cls:
            if item.value == value:
                return item
        raise ValueError(f"No corresponding enum for value: {value}")

class Spike_Type(TypeUtilities):
    CPU = 'c'
    RAM = 'r'
    IFACE_TRAFFIC = 't'
    THROUGHPUT = 'b'
    PACKET_LOSS = 'p'
    JITTER = 'j'

class AlertFlow_Report:

    def __init__(self, deviceID, taskID, spike_types: list, interfaces=[]):
        
        spike_enums = []
        for spike_type in spike_types:
            spike_enum = Spike_Type.corresponds(spike_type)
            if spike_enum == Spike_Type.IFACE_TRAFFIC and len(interfaces) == 0:
                raise ValueError(
                    f"[AlertFlow]\n | Error: {deviceID}-{taskID} attempted traffic spike report without specifying interfaces."
                )
            spike_enums.append(spike_enum)

        self.report = {
            'di': deviceID,
            'ti': taskID,
            's': [spike.value for spike in spike_enums]
        }

        if Spike_Type.IFACE_TRAFFIC in spike_enums:
            self.report['i'] = interfaces

    def __str__(self):
        string = [
            Colours.alertflow_styling(f"[AlertFlow: Device {self.report['di']} - Task {self.report['ti']}]"),
            f" | Spiked: {', '.join([Spike_Type.corresponds(spike).name for spike in self.report['s']])}",
        ]

        if 'i' in self.report:
            string.append(f" | Affected Interfaces: {', '.join(self.report['i'])}")

        return "\n".join(string)

    def deviceID(self):
        return self.report['di']
    
    def taskID(self):
        return self.report['ti']

    def serialize(self) -> bytes:
        return compress(packb(self.report, use_bin_type=True))

    @staticmethod
    def deserialize(data: bytes) -> 'AlertFlow_Report':
        unpacked_data = unpackb(decompress(data), raw=False)
        return AlertFlow_Report(
            deviceID=unpacked_data['di'],
            taskID=unpacked_data['ti'],
            spike_types=unpacked_data['s'],
            interfaces=unpacked_data.get('i', [])
        )

    def to_full_dict(self) -> dict:
        full_dict = {
            'device_id': self.report['di'],
            'task_id': self.report['ti'],
            'spikes': [Spike_Type.corresponds(spike).name for spike in self.report['s']],
        }

        if 'i' in self.report:
            full_dict['interfaces'] = self.report['i']

        return full_dict






if __name__ == "__main__":


    # Test 1: Create a report with multiple spike types
    report1 = AlertFlow_Report(deviceID="device123", taskID="task001", spike_types=['c', 'r'])
    print("Test 1 - Report with multiple spike types:")
    print(report1)

    print("\n" + "-"*50 + "\n")

    # Test 2: Create a report with traffic spike and interfaces
    report2 = AlertFlow_Report(deviceID="device456", taskID="task002", spike_types=['c', 't'], interfaces=['eth0', 'eth1'])
    print("Test 2 - Report with traffic spike and interfaces:")
    print(report2)

    print("\n" + "-"*50 + "\n")

    # Test 3: Serialize and deserialize a report
    serialized_report = report1.serialize()
    print("Test 3 - Serialized Report:")
    print(serialized_report)

    deserialized_report = AlertFlow_Report.deserialize(serialized_report)
    print("Test 3 - Deserialized Report:")
