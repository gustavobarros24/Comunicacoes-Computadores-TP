from typing import Dict, List
from utils import timewindow, Colours

from threading import Thread
from copy import deepcopy

import psutil
from time import sleep

from nettask_task import NetTask_Task
from nettask_report import NetTask_Report















class NetTask_Task_Runner:

    deviceID: str
    local_ifaces: List[str] = list(psutil.net_io_counters(pernic=True).keys())

    def __init__(self, deviceID, task: NetTask_Task, report_enqueuing_method):

        def check_for_unavailable_ifaces():
            requested_ifaces = task.interfaces
            unavailable_ifaces = list(set(requested_ifaces) - set(self.local_ifaces))

            if len(unavailable_ifaces) != 0:
                raise ValueError(
                    f"Error: {task.taskID} requests [{', '.join(task.interfaces)}] but [{', '.join(unavailable_ifaces)}] don't exist here. They'll be ignored."
                )
        
        def gather_relevant_thread_methods():

            l = []

            if self.task.measure_cpu == True:
                l.append((self.cpu_load, ()))
            if self.task.measure_ram == True:
                l.append((self.mem_load, ()))
            if len(self.task.interfaces) != 0:
                l.append((self.ifaces_traffic, (self.task.interfaces,)))

            return l

        self.deviceID = deviceID
        check_for_unavailable_ifaces()
        self.task = deepcopy(task)
        self.duration = self.task.report_frequency
        self.relevant_methods = gather_relevant_thread_methods()
        self.latest_report: NetTask_Report = NetTask_Report(self.deviceID, self.task.taskID)        

        self.enqueue = report_enqueuing_method
        self.thread = Thread(target=self.run_continuously, daemon=True)
        self.thread.start()

    ###############################################################################

    def __str__(self):

        return str(self.latest_report)

    ###############################################################################

    def run_continuously(self):
        print(Colours.nettask_styling(f"[Task {self.task.taskID} is now running]"))

        while True:
            #begin = time()
            self.run_measurements_once()
            #print(self)
            #print(Colours.nettask_styling(f"[Elapsed: {time()-begin}]"))
            
            af_attempt = self.latest_report.attempt_alertflow_report(
                self.task.get_alertflow_thresholds()
            )
            
            #if af_attempt is not None:
            #    print(f"{af_attempt}\n")

            self.enqueue(self.latest_report, af_attempt)

    def run_measurements_once(self):
        
        threads = [
                Thread(target=method, args=args)
                for method,args in self.relevant_methods
            ]

        #print(f"{threads[0].name} through {threads[-1].name}")
        
        try:
            for t in threads:
                try:
                    t.start()
                except Exception as e:
                    print(f"Error starting thread {t.name}: {e}")

            for t in threads:
                try:
                    t.join()
                except Exception as e:
                    print(f"Error joining thread {t.name}: {e}")

        except Exception as e:
            print(f"Unexpected error during thread management: {e}")    

    def cpu_load(self):
        self.latest_report.add_measurement(
            'c', psutil.cpu_percent(interval=self.duration)
        )

    def mem_load(self):

        load_sum = 0
        for _ in range(self.duration):
            load_sum += timewindow(psutil.virtual_memory, 1).percent

        self.latest_report.add_measurement('r', round(load_sum/self.duration,1))

    def ifaces_traffic(self, ifaces):
        
        def get_current_traffic():

            net_io_counters = psutil.net_io_counters(pernic=True)
            
            return {
                k: net_io_counters[k].packets_recv + net_io_counters[k].packets_sent 
                for k in net_io_counters.keys() if k in ifaces
            }
        
        initial = get_current_traffic()
        sleep(self.duration)
        final = get_current_traffic()
            
        self.latest_report.add_measurement(
            't', {
            iface: round((final[iface]-initial[iface])/self.duration, 1)
            for iface in initial.keys()
        }) # map {iterface: bidirectional traffic in packets/second}

    ###############################################################################

    def taskID(self):
        return self.task.taskID































if __name__ == "__main__":

    task_data_1 = {
        "taskID": "t1",
        "report_frequency": 5,
        "devices": ["r1", "r2"],  # Ignored
        "measure_cpu": True,
        "measure_ram": True,
        "device_interfaces": ["eth0", "eth1"],
        "iperf_measure_throughput": True,
        "iperf_measure_jitter": True,
        "iperf_measure_packet_loss": True,
        "ping_measure_latency": True,
        "iperf_as_server": True,
        "iperf_options": None,
        "ping_options": None,
        "alertflow_cpu_percent": 1,#90,
        "alertflow_ram_percent": None,
        "alertflow_interface_pps": 1,#2000,
        "alertflow_packetloss_percent": 50,
        "alertflow_jitter_ms": 10,
        "alertflow_latency_ms": 90
    }

    task_data_2 = {
        "taskID": "t2",
        "report_frequency": 10,
        "devices": ["r3"],  # Ignored
        "measure_cpu": False,
        "measure_ram": True,
        "device_interfaces": ["eth2", "eth3"],
        "iperf_measure_throughput": False,
        "iperf_measure_jitter": True,
        "iperf_measure_packet_loss": False,
        "ping_measure_latency": True,
        "iperf_as_server": False,
        "iperf_options": None,
        "ping_options": None,
        "alertflow_cpu_percent": 80,
        "alertflow_ram_percent": None,
        "alertflow_interface_pps": 1500,
        "alertflow_packetloss_percent": 30,
        "alertflow_jitter_ms": 15,
        "alertflow_latency_ms": 100
    }

    threads = [
        Thread(target=NetTask_Task_Runner, args=("r1",NetTask_Task.from_json(task_data_1)), daemon=True),
        Thread(target=NetTask_Task_Runner, args=("r1",NetTask_Task.from_json(task_data_2)), daemon=True)
    ]

    # Start all threads
    for t in threads:
        t.start()

    # Join all threads (optional, allows clean exit)
    for t in threads:
        t.join()