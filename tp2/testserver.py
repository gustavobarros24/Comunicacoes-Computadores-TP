from nettask_task import NetTask_Task
from nettask_message import NetTask_Message
from nettask_report import NetTask_Report

from alertflow_report import AlertFlow_Report

from socketwrapper import SocketWrapper
from datagram import Datagram, Flags
from utils import NETTASK_SERVER_PORT, get_local_addr, randint_excluding, print_directory

from typing import List, Set, Tuple, Dict
from threading import Thread
from socket import socket, AF_INET, SOCK_STREAM

import json
import os
import shutil
from datetime import datetime

LOGS_BASE_DIR = "logs"












class Server_Worker:
    def __init__(self, port: int, syn: Datagram, fetch_tasks_method):
        
        
        self.nettask_socket = SocketWrapper(local_addr=get_local_addr(), local_port=port)
        self.agent_addr = syn.origin.addr
        self.agent_port = syn.origin.port
        
        self.agent_deviceID: str = None
        self.tasks: Dict[str, NetTask_Task] = None
        self.fetch_tasks = fetch_tasks_method
        
        
        self.alertflow_socket = socket(AF_INET, SOCK_STREAM)
        self.alertflow_socket.bind((get_local_addr(), port))
        self.alertflow_thread = Thread(target=self.listen_for_spikes, daemon=True)
        self.alertflow_peer_socket: socket = None

        self.worker_thread = Thread(target=self.begin, args=(syn,), daemon=True)
        self.worker_thread.start()

        self.worker_is_alive = True

    ###########################################################################################################

    def listen_for_nettask_control_message(self) -> str:
        while True:
            self.portprint("Blockingly listening for an empty message.")
            datagram, _ = self.nettask_socket.receive()
            if not datagram or datagram.payload_size()==0:
                continue
                     
            ntmessage = NetTask_Message.deserialize(datagram.payload)
            self.portprint(f"Got a message! {ntmessage}")
            if ntmessage is not None and ntmessage.contains_only_header():
                self.nettask_socket.send_ack(datagram)
                return str(ntmessage.author)
            else:
                self.portprint("Received something other than a bare message. Ignored.")

    def send_tasks(self):
        def send_single_task(task: NetTask_Task, is_last=False):
            ntmessage = NetTask_Message(author=self.agent_addr, tag='f' if is_last else 't', payload=task.serialize())
            self.send_data(ntmessage.serialize())

        tasks = list(self.tasks.values())
        for idx, task in enumerate(tasks):
            send_single_task(task, is_last=(idx == len(tasks) - 1))

    def start_alertflow(self):
        
        while True:
            self.portprint(f"Awaiting AlertFlow connection from {self.agent_addr}:{self.agent_port}")
            self.alertflow_socket.listen(1)
            peer_socket, peer_name = self.alertflow_socket.accept()
            if peer_name[0] == self.agent_addr and peer_name[1] == self.agent_port:
                self.portprint("AlertFlow connection achieved!")
                self.alertflow_peer_socket = peer_socket
                break
            else:
                self.portprint(f"Incorrectly received connection attempt from {peer_name[0]}:{peer_name[1]}.")
                peer_socket.close()

        self.alertflow_thread.start()

    def listen_for_reports(self):
        while True:
            self.portprint("Blockingly listening for a report.")
            datagram, _ = self.nettask_socket.receive()
            if not datagram or datagram.payload_size()==0:
                continue
                        
            ntmessage = NetTask_Message.deserialize(datagram.payload)
            self.portprint(f"Got a message! {ntmessage}")
            if ntmessage is not None and ntmessage.contains_report():
                self.nettask_socket.send_ack(datagram)
                self.add_report_to_logfile(NetTask_Report.deserialize(ntmessage.payload))
            else:
                self.portprint("Received something other than a report. Ignored.")

    def listen_for_spikes(self):
        while self.worker_is_alive:
            self.portprint("(ALERTFLOW) Blockingly listening for a spike report.")
            report: AlertFlow_Report = AlertFlow_Report.deserialize(self.alertflow_peer_socket.recv(1024))
            self.add_spike_to_spikefile(report)

    def send_data(self, payload):
        self.nettask_socket.send_and_wait_ack(
            self.agent_addr, self.agent_port, Flags(syn=False, ack=True, fin=False), payload=payload
        )
    
    ########################################################################################################### 

    def add_report_to_logfile(self, report: NetTask_Report):

        print(report)
        device_dir = os.path.join(LOGS_BASE_DIR, report.deviceID)
        task_file_path = os.path.join(device_dir, f"{report.taskID}.json")

        # Ensure the device directory exists
        os.makedirs(device_dir, exist_ok=True)

        # Load existing data from the JSON file if it exists
        if os.path.exists(task_file_path):
            with open(task_file_path, "r") as task_file:
                try:
                    existing_data = json.load(task_file)
                except json.JSONDecodeError:
                    existing_data = {} 
        else:
            existing_data = {}

        existing_data[str(datetime.now())] = report.to_dict()

        with open(task_file_path, "w") as task_file:
            json.dump(existing_data, task_file, indent=4)    

    def add_spike_to_spikefile(self, report: AlertFlow_Report):
        
        print(report)
        device_dir = os.path.join(LOGS_BASE_DIR, report.deviceID())
        spike_file_path = os.path.join(device_dir, f"{report.taskID()}spikes.json")

        # Ensure the device directory exists
        os.makedirs(device_dir, exist_ok=True)

        # Load existing data from the JSON file if it exists
        if os.path.exists(spike_file_path):
            with open(spike_file_path, "r") as spike_file:
                try:
                    existing_data: Dict = json.load(spike_file)
                except json.JSONDecodeError:
                    existing_data: Dict = {}  # If file is empty or corrupted, initialize as empty list
        else:
            existing_data: Dict = {}

        # Append the new report's dictionary representation to the data
        existing_data[str(datetime.now())] = report.to_full_dict()

        # Write the updated data back to the file
        with open(spike_file_path, "w") as spike_file:
            json.dump(existing_data, spike_file, indent=4)

    ###########################################################################################################

    def portprint(self, string):
        self.nettask_socket.sockprint(string, self.agent_deviceID if self.agent_deviceID is not None else None)

    ###########################################################################################################

    def begin(self, syn):
        self.portprint(f"A server worker is born.")

        # send synack and receive ack back
        self.nettask_socket.send_ack(syn)
        self.portprint(f"Handshake complete. Will listen for empty NT message to retrieve deviceID.")
        
        # obtain agent's deviceID
        self.agent_deviceID = self.listen_for_nettask_control_message()
        self.portprint(f"Obtained the agent's deviceID: {self.agent_deviceID}. Will be sending its tasks up next.")
        
        # obtain deviceID's corresponding tasks
        self.tasks = self.fetch_tasks(self.agent_deviceID)
        for k,v in self.tasks.items(): print(v)

        # send the tasks one at a time
        self.send_tasks()
        self.portprint("All tasks sent. Will establish AlertFlow connection next.")

        # establish connection with the agent's AlertFlow socket
        self.start_alertflow()
        self.portprint("AlertFLow connection achieved! Will be awaiting reports.")

        # store the incoming reports
        self.listen_for_reports()












class Server:

    def __init__(self, config_filepath):


        self.tasks: Dict[str, NetTask_Task] = {}
        self.device_to_tasks: Dict[str, List[str]] = {}  # tasks assigned to each device
        self.task_to_devices: Dict[str, List[str]] = {}  # devices assigned to each task

        self.load_config(config_filepath)
        self.create_logfiles()

        self.host = get_local_addr()
        self.nettask_port = NETTASK_SERVER_PORT
        self.entry_socket = SocketWrapper(local_addr=self.host, local_port=self.nettask_port)
        print(f"Server listening on {self.host}:{self.nettask_port}")        

        self.used_ports: set = {NETTASK_SERVER_PORT}
        self.current_connections: dict = {}

    ###########################################################################################################

    def entry_listen(self):
        while True:
            datagram, addr = self.entry_socket.receive()
            if not datagram: continue
    
            if datagram.is_syn():
                print(f"Received SYN from {addr}")
                self.new_worker(datagram)
    
            elif datagram.is_fin():
                self.portprint(f"Received FIN from {addr}")
                self.entry_socket.send_ack(datagram)
                break

            elif len(datagram.payload)>0:
                self.portprint(f"Received message: {datagram.payload.decode()} from {addr}. This port isn't for data!")      

    def close(self):
        self.entry_socket.close()
        print("Server entry_socket closed.")

    ###########################################################################################################

    def fetch_tasks(self, deviceID) -> Dict[str, NetTask_Task]:
        taskIDs_for_this_device = self.device_to_tasks[deviceID]
        return {
            k: v
            for k, v in self.tasks.items()
            if k in taskIDs_for_this_device
        }

    def new_worker(self, syn: Datagram):
    
        self.portprint(f"Entering new_worker for the following syn: {syn}")
        new_worker_port = randint_excluding(49152,65535,self.used_ports)
        
        worker = Server_Worker(port=new_worker_port, syn=syn, fetch_tasks_method=self.fetch_tasks)

        self.used_ports.add(new_worker_port)
        self.current_connections[syn.origin.addr] = worker

    ###########################################################################################################

    def load_config(self, config_file: str):
        with open(config_file, 'r') as file:
            config_data = json.load(file)

        # Iterate through each task and load it
        for task in config_data["tasks"]:
            taskID = task["taskID"]
            task_devices = task["devices"]
            
            # Add task to the tasks dictionary
            self.tasks[taskID] = NetTask_Task.from_json(task)
            
            # Add taskID to the list of tasks for each device
            for device in task_devices:
                # Add taskID to the device-to-task mapping
                if device not in self.device_to_tasks:
                    self.device_to_tasks[device] = []  # Initialize the list if not exists
                self.device_to_tasks[device].append(taskID)
                
                # Add device to the task-to-device mapping
                if taskID not in self.task_to_devices:
                    self.task_to_devices[taskID] = []  # Initialize the list if not exists
                self.task_to_devices[taskID].append(device)

    def create_logfiles(self):
        os.makedirs(LOGS_BASE_DIR, exist_ok=True)  # Ensure the base directory exists

        # Iterate through the device-to-tasks mapping
        for device, task_ids in self.device_to_tasks.items():
            # Create a directory for the device
            device_dir = os.path.join(LOGS_BASE_DIR, device)
            os.makedirs(device_dir, exist_ok=True)

            # Create an empty JSON file for each task assigned to the device
            for task_id in task_ids:
                task_file_path = os.path.join(device_dir, f"{task_id}.json")
                spike_file_path = os.path.join(device_dir, f"{task_id}spikes.json")
                with open(task_file_path, "w") as task_file:
                    json.dump({}, task_file, indent=4)  # Write an empty JSON object
                with open(spike_file_path, "w") as spike_file:
                    json.dump({}, spike_file, indent=4)    


        print_directory(LOGS_BASE_DIR)

    def delete_log_dir():   
        if os.path.exists(LOGS_BASE_DIR):  # Check if the directory exists
            shutil.rmtree(LOGS_BASE_DIR)  # Delete the directory
    
    ###########################################################################################################

    def portprint(self, string):
        self.entry_socket.sockprint(string)

    












if __name__ == "__main__":
    
    Server.delete_log_dir()

    config_filepath = "config.json"
    server = Server(config_filepath)
    try:
        server.entry_listen()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        server.close()

