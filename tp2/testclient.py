from typing import Dict

from socketwrapper import SocketWrapper
from datagram import Flags, Datagram
from utils import get_local_addr, Colours, NETTASK_SERVER_PORT

from nettask_message import NetTask_Message
from nettask_report import NetTask_Report
from nettask_task import NetTask_Task
from nettask_task_runner import NetTask_Task_Runner

from alertflow_report import AlertFlow_Report

from socket import socket, AF_INET, SOCK_STREAM
from threading import Thread
from queue import Queue

import sys

class Client:
    def __init__(self, server_host, deviceID, port):
        
        ###### NetTask-Related #######################
        self.server_host = server_host
        self.server_port = NETTASK_SERVER_PORT
        self.nettask_socket = SocketWrapper(local_addr=get_local_addr(server_host), local_port=port)
        self.nettask_report_queue: Queue[NetTask_Report] = Queue()
        
        ###### AlertFlow-Related #####################
        self.alertflow_socket = socket(AF_INET, SOCK_STREAM)
        self.alertflow_socket.bind((get_local_addr(server_host), port))
        self.alertflow_report_queue: Queue[AlertFlow_Report] = Queue()

        ###### Tasks/Reports #########################
        self.deviceID = deviceID
        self.reports_to_send = None

        self.tasks: Dict[str, NetTask_Task] = {} # taskID -> task
        self.task_runners: Dict[str, NetTask_Task_Runner] = {} # taskID -> taskrunner thread

    # Threaded Report Sending ###################################################################

    def send_enqueued_reports(self):
        
        # AlertFlow report sending will happen in a thread parallel to the main one, which will send the NetTask reports.
        def alertflow_sender_thread():
            try:
                while True:
                    report: AlertFlow_Report = self.alertflow_report_queue.get()
                    print(report)
                    self.alertflow_socket.sendall(report.serialize())
            except KeyboardInterrupt:
                pass

        af_thread = Thread(target=alertflow_sender_thread, daemon=True)
        af_thread.start()

        try:
            while True:
                report: NetTask_Report = self.nettask_report_queue.get()
                print(report)
                ntmessage: NetTask_Message = NetTask_Message(author=self.deviceID, tag='r', payload=report.serialize())
                self.nettask_socket.send_and_wait_ack(
                    dest_addr=self.server_host,
                    dest_port=self.server_port,
                    flags=Flags(False, True, False),
                    payload=ntmessage.serialize()
                )
        except KeyboardInterrupt:
            pass                        

    def instantiate_task_runners(self):

        for tID, t in self.tasks.items():
            new_runner = NetTask_Task_Runner(
                deviceID=self.deviceID,
                task=t,
                report_enqueuing_method=self.enqueue_report
            )
            self.task_runners[tID] = new_runner

    def enqueue_report(self, nt_report, af_report=None):        
        self.nettask_report_queue.put(nt_report)
        if af_report is not None:
            self.alertflow_report_queue.put(af_report)

    # Initial Communication #####################################################################

    def handshake(self):
        synack_received: Datagram = self.nettask_socket.send_and_wait_ack(
            dest_addr=self.server_host, dest_port=self.server_port, flags=Flags(syn=True, ack=False, fin=False)
        )
        # The synack is received from a port other than 9000, thus we update the new port of communication
        self.server_port = synack_received.origin.port
        print(f"New server port: {self.server_port}")
        self.nettask_socket.send_ack(synack_received)

    def send_nettask_control_message(self):

        msg = NetTask_Message(author=self.deviceID,tag='c')
        payload = msg.serialize()

        print(f"Sending empty NetTask message as payload of size: {len(payload)} B")
        self.nettask_socket.send_and_wait_ack(
            self.server_host, self.server_port, Flags(syn=False, ack=True, fin=False),
            payload=payload
        )

    def listen_for_nettask_tasks(self):
        
        def collect_task(ntmessage: NetTask_Message) -> str:
            task = NetTask_Task.deserialize(ntmessage.payload)
            self.tasks[task.taskID] = task
            return task.taskID
        
        print("Ready to receive tasks.")

        while True:
            datagram, _ = self.nettask_socket.receive()
            if not datagram or datagram.payload_size()==0: continue
            
            ntmessage = NetTask_Message.deserialize(datagram.payload)
            print(ntmessage)

            contains_task, is_final_task = ntmessage.contains_task()
            if contains_task:
                self.nettask_socket.send_ack(datagram)
                taskID = collect_task(ntmessage)
                print(f"A task was collected: {self.tasks[taskID]}")

                if is_final_task:
                    print("Received the final task.")
                    break

    def connect_alertflow(self):
        print("Attempting connection to AlertFlow socket.")
        self.alertflow_socket.connect((self.server_host, self.server_port))

    def close(self):
        self.nettask_socket.send_and_wait_ack(
            self.server_host, self.server_port, Flags(syn=False, ack=False, fin=True)
        )
        self.nettask_socket.close()





































    #############################################################################################

if __name__ == "__main__":

    if len(sys.argv) != 3:
        print("Usage: python3 testclient.py <server_host> <deviceID> <port>")
        sys.exit(1)
    
    # Extract command-line arguments
    server_host = sys.argv[1]
    deviceID = sys.argv[2]
    
    client = Client(server_host, deviceID, port=2000)
    
    client.handshake()
    print("Handshake done!")

    # The NetTask message header contains the deviceID, so we send one with empty payload just for serverside recon. 
    # The server worker needs to be aware of this machine's deviceID to send the corresponding tasks.
    client.send_nettask_control_message()
    client.listen_for_nettask_tasks()
    
    client.connect_alertflow()

    client.instantiate_task_runners()
    client.send_enqueued_reports()
    
    client.close()

