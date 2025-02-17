from typing import List, Optional, NamedTuple
from collections import namedtuple

from msgpack import packb, unpackb
from zlib_ng.zlib_ng import compress, decompress


















class NetTask_Task:

    def __init__(
        self, 
        taskID: str, 
        report_frequency: int, 
        measure_cpu: bool = False, 
        measure_ram: bool = False, 
        interfaces: List[str] = None, 
        iperf_measure_throughput: bool = False, 
        iperf_measure_jitter: bool = False, 
        iperf_measure_packet_loss: bool = False, 
        ping_measure_latency: bool = False, 
        iperf_as_server: bool = False, 
        iperf_options: Optional[str] = None, 
        ping_options: Optional[str] = None, 
        alertflow_cpu_percent: int = 0, 
        alertflow_ram_percent: int = 0, 
        alertflow_interface_pps: int = 0, 
        alertflow_packetloss_percent: int = 0, 
        alertflow_jitter_ms: int = 0, 
        alertflow_latency_ms: int = 0
    ):
        self.taskID = taskID
        self.report_frequency = report_frequency
        self.measure_cpu = measure_cpu
        self.measure_ram = measure_ram
        self.interfaces = interfaces if interfaces is not None else []
        self.iperf_measure_throughput = iperf_measure_throughput
        self.iperf_measure_jitter = iperf_measure_jitter
        self.iperf_measure_packet_loss = iperf_measure_packet_loss
        self.ping_measure_latency = ping_measure_latency
        self.iperf_as_server = iperf_as_server
        self.iperf_options = iperf_options
        self.ping_options = ping_options
        self.alertflow_cpu_percent = alertflow_cpu_percent
        self.alertflow_ram_percent = alertflow_ram_percent
        self.alertflow_interface_pps = alertflow_interface_pps
        self.alertflow_packetloss_percent = alertflow_packetloss_percent
        self.alertflow_jitter_ms = alertflow_jitter_ms
        self.alertflow_latency_ms = alertflow_latency_ms

    @classmethod
    def from_json(cls, task_data: dict) -> "NetTask_Task":

        return cls(
            taskID=task_data["taskID"],
            report_frequency=task_data["report_frequency"],
            measure_cpu=task_data.get("measure_cpu", False),
            measure_ram=task_data.get("measure_ram", False),
            interfaces=task_data.get("device_interfaces", []),
            iperf_measure_throughput=task_data.get("iperf_measure_throughput", False),
            iperf_measure_jitter=task_data.get("iperf_measure_jitter", False),
            iperf_measure_packet_loss=task_data.get("iperf_measure_packet_loss", False),
            ping_measure_latency=task_data.get("ping_measure_latency", False),
            iperf_as_server=task_data.get("iperf_as_server", False),
            iperf_options=task_data.get("iperf_options"),
            ping_options=task_data.get("ping_options"),
            alertflow_cpu_percent=task_data.get("alertflow_cpu_percent"),
            alertflow_ram_percent=task_data.get("alertflow_ram_percent"),
            alertflow_interface_pps=task_data.get("alertflow_interface_pps"),
            alertflow_packetloss_percent=task_data.get("alertflow_packetloss_percent"),
            alertflow_jitter_ms=task_data.get("alertflow_jitter_ms"),
            alertflow_latency_ms=task_data.get("alertflow_latency_ms")
        )
        
    def __str__(self):
        
        def show_threshold(enabled: bool, threshold_value: int, unit: str):

            if not enabled:
                return f"Disabled"
            else:
                alertflow = "AlertFlow OFF" if threshold_value is None else f"AlertFlow Threshold: {threshold_value}{unit}" 
                return f"Enabled ({alertflow})"
        
        def interfaces_show_threshold(threshold_value: int, unit: str):
            return "(AlertFlow OFF)" if threshold_value is None else f"(AlertFlow Threshold: {threshold_value} {unit})"

        return "\n".join([
            f"NetTask_Task: {self.taskID}",
            f" | Report Frequency: {self.report_frequency}s",
            
            f" | Measurements:",
            f" |  | CPU: {show_threshold(self.measure_cpu, self.alertflow_cpu_percent, '%')}",
            f" |  | RAM: {show_threshold(self.measure_ram, self.alertflow_ram_percent, '%')}",
            f" |  | Interfaces: {', '.join(self.interfaces) if self.interfaces else 'N/A'} {interfaces_show_threshold(self.alertflow_interface_pps, 'packets/s')}",
            
            f" |  | iPerf:",
            f" |  |  | Throughput: {'Enabled' if self.iperf_measure_throughput else 'Disabled'}",
            f" |  |  | Jitter: {show_threshold(self.iperf_measure_jitter, self.alertflow_jitter_ms, 'ms')}",
            f" |  |  | Packet Loss: {show_threshold(self.iperf_measure_packet_loss, self.alertflow_packetloss_percent, '%')}",
            f" |  |  | Server Mode: {'Enabled' if self.iperf_as_server else 'Disabled'}",
            f" |  |  | Options: {self.iperf_options if self.iperf_options else 'None'}",
            
            f" |  | Ping:",
            f" |  |  | Latency: {show_threshold(self.ping_measure_latency, self.alertflow_latency_ms, 'ms')}",
            f" |  |  | Options: {self.ping_options if self.ping_options else 'None'}",
        ])

    def get_alertflow_thresholds(self):

        thresholds = {}

        if self.measure_cpu == True and self.alertflow_cpu_percent is not None:
            thresholds['c'] = self.alertflow_cpu_percent
        if self.measure_ram == True and self.alertflow_ram_percent is not None:
            thresholds['r'] = self.alertflow_ram_percent
        if len(self.interfaces) != 0 and self.alertflow_interface_pps is not None:
            thresholds['t'] = self.alertflow_interface_pps
        
        return thresholds

    def serialize(self):
            
        return compress(packb({
            'ti': self.taskID,
            'rf': self.report_frequency,
            'c' : [self.measure_cpu, self.alertflow_cpu_percent],
            'r' : [self.measure_ram, self.alertflow_ram_percent],
            't' : [self.interfaces, self.alertflow_interface_pps],
            'b' : self.iperf_measure_throughput,
            'j' : [self.iperf_measure_jitter, self.alertflow_jitter_ms],
            'p' : [self.iperf_measure_packet_loss, self.alertflow_packetloss_percent],
            'l' : [self.ping_measure_latency, self.alertflow_latency_ms],
            's' : self.iperf_as_server,
            'oi': self.iperf_options,
            'op': self.ping_options
        }, use_bin_type=True, strict_types=True))

    @classmethod
    def deserialize(cls, serialized_data: bytes) -> "NetTask_Task":
        # Uncompress and unpack the data
        data_dict = unpackb(decompress(serialized_data), raw=False)
        
        # Extract values from the dictionary and map them back to the NetTask_Task constructor
        return cls(
            taskID=data_dict['ti'],
            report_frequency=data_dict['rf'],
            measure_cpu=data_dict['c'][0],
            alertflow_cpu_percent=data_dict['c'][1],
            measure_ram=data_dict['r'][0],
            alertflow_ram_percent=data_dict['r'][1],
            interfaces=data_dict['t'][0],
            alertflow_interface_pps=data_dict['t'][1],
            iperf_measure_throughput=data_dict['b'],
            iperf_measure_jitter=data_dict['j'][0],
            alertflow_jitter_ms=data_dict['j'][1],
            iperf_measure_packet_loss=data_dict['p'][0],
            alertflow_packetloss_percent=data_dict['p'][1],
            ping_measure_latency=data_dict['l'][0],
            alertflow_latency_ms=data_dict['l'][1],
            iperf_as_server=data_dict['s'],
            iperf_options=data_dict['oi'],
            ping_options=data_dict['op']
        )

































if __name__ == "__main__":

    # Complete example task data with iperf and ping options
    task_data = {
        "taskID": "t2",
        "report_frequency": 10,
        "devices": ["r3", "r4"],  # Ignored
        "measure_cpu": True,
        "measure_ram": False,
        "device_interfaces": ["eth1", "eth2"],
        "iperf_measure_throughput": True,
        "iperf_measure_jitter": False,
        "iperf_measure_packet_loss": True,
        "ping_measure_latency": True,
        "iperf_as_server": False,
        "iperf_options": "-t 30 -u -b 100M",  # iPerf options for testing with UDP, 30 seconds, 100 Mbps bandwidth
        "ping_options": "-c 5 -i 0.5",  # Ping options to send 5 packets with 0.5 second interval
        "alertflow_cpu_percent": 85,
        "alertflow_ram_percent": None,
        "alertflow_interface_pps": 3000,
        "alertflow_packetloss_percent": 10,
        "alertflow_jitter_ms": 20,
        "alertflow_latency_ms": 50
    }

    # Create NetTask_Task object from JSON
    task = NetTask_Task.from_json(task_data)

    # Print the task details using the __str__ method
    print("NetTask_Task from JSON:\n", task)

    # Serialize the NetTask_Task to test serialization
    serialized_data = task.serialize()
    print("\nSerialized NetTask_Task size:", len(serialized_data))

    # Deserialize the data back into a NetTask_Task object
    deserialized_task = NetTask_Task.deserialize(serialized_data)

    # Print the deserialized task details
    print("\nDeserialized NetTask_Task:\n", deserialized_task)

