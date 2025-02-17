from time import time, sleep
from directory_tree import DisplayTree
from random import randint
from socket import socket, AF_INET, SOCK_DGRAM

NETTASK_SERVER_PORT = 9000

def timewindow(func, duration, *args, **kwargs):
    start_time = time()                 # Record the start time
    result = func(*args, **kwargs)      # Call the function and get its result
    elapsed_time = time() - start_time  # Measure how long the function took
    #print(f"Callee took {elapsed_time} seconds")
    
    # If the function completed faster than the duration, wait the remaining time
    if elapsed_time < duration:
    #    print(f"I'll sit around for {duration-elapsed_time} seconds")
        sleep(duration - elapsed_time)

    return result

def print_directory(directory: str):
    DisplayTree(directory) # ex: "./myfolder" prints the tree starting with myfolder as root

class Colours:
    """ ANSI color codes """
    BLACK = "\033[0;30m"
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    BROWN = "\033[0;33m"
    BLUE = "\033[0;34m"
    PURPLE = "\033[0;35m"
    CYAN = "\033[0;36m"
    LIGHT_GRAY = "\033[0;37m"
    DARK_GRAY = "\033[1;30m"
    LIGHT_RED = "\033[1;31m"
    LIGHT_GREEN = "\033[1;32m"
    YELLOW = "\033[1;33m"
    LIGHT_BLUE = "\033[1;34m"
    LIGHT_PURPLE = "\033[1;35m"
    LIGHT_CYAN = "\033[1;36m"
    LIGHT_WHITE = "\033[1;37m"
    BOLD = "\033[1m"
    FAINT = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"
    NEGATIVE = "\033[7m"
    CROSSED = "\033[9m"
    END = "\033[0m"

    @staticmethod
    def nettask_styling(string):
        return Colours.GREEN + Colours.BOLD + string + Colours.END

    @staticmethod
    def alertflow_styling(string):
        return Colours.RED + Colours.BOLD + string + Colours.END

def randint_excluding(start, stop, excluded) -> int:
    """Function for getting a random number with some numbers excluded"""
    excluded = set(excluded)
    value = randint(start, stop - len(excluded))
    for exclusion in tuple(excluded):
        if value < exclusion:
            break
        value += 1
    return value

def get_local_addr(dest_addr=None) -> str:
    
    connect_to = (dest_addr if dest_addr is not None else '8.8.8.8', 80)

    s = socket(AF_INET, SOCK_DGRAM)
    s.connect(connect_to)
    
    return s.getsockname()[0]
        

if __name__ == "__main__":

    # Example function that takes arguments
    def process_data(data, delay=2):
        """
        Simulates processing data with a delay.
        Args:
            data: The data to process.
            delay: Time (in seconds) to simulate processing.
        """
        sleep(delay)  # Simulate a delay
        return f"Processed: {data}"

    # Use starter with arguments
    result = timewindow(func=process_data, duration=5, data="Sample Data", delay=3)
    print(result)