from utils import Colours
from typing import Dict, List
from copy import deepcopy

from msgpack import packb, unpackb
from zlib_ng.zlib_ng import compress, decompress

from alertflow_report import AlertFlow_Report



















all_possible_measurements = ['c', 'r', 't']

measure_labels = {
    'c': "CPU",
    'r': "RAM",
    't': "Interface Traffic"
}


class NetTask_Report:

    def __init__(self, deviceID, taskID):
        self.deviceID = deviceID
        self.taskID = taskID
        self.measurements: Dict = {}
    
    def __str__(self):

        def format(key, value):

            if key in {'c', 'r'}:
                return f"{measure_labels[key]}: {value}%"
            elif key == 't':
                return (
                    f"Interfaces:\n | | " + "\n | | ".join(
                        f"{iface}: {traffic} packets/s"
                        for iface, traffic in self.measurements['t'].items()
                    )
                )

        title_str = Colours.nettask_styling(f"[NetTask: Device {self.deviceID} - Task {self.taskID}]")

        measurements_str = "\n | ".join([
            format(key, self.measurements[key]) 
            for key in all_possible_measurements 
            if key in self.measurements
        ])

        return title_str + "\n | " + measurements_str

    def to_dict(self):
        
        return {
            measure_labels[key]: self.measurements[key]
            for key in all_possible_measurements
            if key in self.measurements
        }

    def add_measurement(self, key, value):
        self.measurements[key] = deepcopy(value) if key == 't' else value

    def serialize(self) -> bytes:
        data = {
            'di': self.deviceID,
            'ti': self.taskID,
            'm': self.measurements
        }

        return compress(packb(data, use_bin_type=True, strict_types=True))

    @staticmethod
    def deserialize(data: bytes) -> 'NetTask_Report':

        unpacked_data = unpackb(decompress(data), raw=False)

        nettask_report = NetTask_Report(
            deviceID=unpacked_data['di'],
            taskID=unpacked_data['ti']
        )

        nettask_report.measurements = unpacked_data['m']

        return nettask_report

    def attempt_alertflow_report(self, alertflow_thresholds: Dict[str, int]):

        def exceeds_threshold(measure, result):
            threshold = alertflow_thresholds.get(measure)
            # Ensure that the threshold is a valid number, if it's None, treat it as no limit (float('inf'))
            threshold = threshold if threshold is not None else float('inf')
            return result >= threshold

        # Get spike types for CPU and RAM
        spike_types = list(
            filter(lambda measure: measure in {'c', 'r'} and exceeds_threshold(measure, self.measurements[measure]),
                self.measurements.keys())
        )

        # Get spiked interfaces for traffic
        spiked_ifaces = list(
            filter(
                lambda iface_traffic: iface_traffic[1] >= alertflow_thresholds.get('t', float('inf')),
                self.measurements.get('t', {}).items()
            )
        )

        # Add 't' to spike types if any interfaces spiked
        if spiked_ifaces:
            spike_types.append('t')

        # If there are spikes, create and return the report
        return AlertFlow_Report(self.deviceID, self.taskID, spike_types, [iface for iface, _ in spiked_ifaces]) if spike_types else None




































if __name__ == "__main__":
    # Sample Test Cases

    # Test 1: Create a NetTask_Report and add some measurements
    print("Test 1: Create a NetTask_Report and add some measurements")
    nettask1 = NetTask_Report(deviceID="dev001", taskID="task001")
    nettask1.add_measurement('c', 80)  # CPU 80%
    nettask1.add_measurement('r', 65)  # RAM 65%
    nettask1.add_measurement('t', {'eth0': 1000, 'eth1': 1500})  # Interface Traffic
    print(nettask1)

    # Test 2: Serialize and Deserialize the report
    print("\nTest 2: Serialize and Deserialize the report")
    serialized_data = nettask1.serialize()
    deserialized_report = NetTask_Report.deserialize(serialized_data)
    print(deserialized_report)

    # Test 3: Attempt AlertFlow report with a threshold that triggers spikes
    print("\nTest 3: Attempt AlertFlow report with a threshold that triggers spikes")
    alertflow_thresholds = {'c': 70, 'r': 60, 't': 1000}
    alertflow_report = nettask1.attempt_alertflow_report(alertflow_thresholds)
    if alertflow_report:
        print(alertflow_report)
    else:
        print("No spikes detected.")

    # Test 4: Attempt AlertFlow report with no spikes
    print("\nTest 4: Attempt AlertFlow report with no spikes")
    alertflow_thresholds_no_spikes = {'c': 90, 'r': 85, 't': 2000}
    alertflow_report_no_spikes = nettask1.attempt_alertflow_report(alertflow_thresholds_no_spikes)
    if alertflow_report_no_spikes:
        print(alertflow_report_no_spikes)
    else:
        print("No spikes detected.")

    # Test 5: Add more measurements and test AlertFlow with multiple spikes
    print("\nTest 5: Add more measurements and test AlertFlow with multiple spikes")
    nettask1.add_measurement('r', 90)  # RAM 90%
    nettask1.add_measurement('t', {'eth0': 1200, 'eth1': 800})  # Interface Traffic

    alertflow_report_multiple_spikes = nettask1.attempt_alertflow_report(alertflow_thresholds)
    if alertflow_report_multiple_spikes:
        print(alertflow_report_multiple_spikes)
    else:
        print("No spikes detected.")

    # Test 6: Edge case - Empty report, no measurements
    print("\nTest 6: Edge case - Empty report, no measurements")
    nettask_empty = NetTask_Report(deviceID="dev002", taskID="task002")
    alertflow_report_empty = nettask_empty.attempt_alertflow_report(alertflow_thresholds)
    if alertflow_report_empty:
        print(alertflow_report_empty)
    else:
        print("No spikes detected.")
