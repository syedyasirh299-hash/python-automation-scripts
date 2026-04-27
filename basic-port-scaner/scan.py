import socket
from datetime import datetime
from plyer import notification

# ANSI color codes for terminal output
GREEN = '\033[92m'   # Green - for open ports
RED = '\033[91m'     # Red - for closed ports
CYAN = '\033[96m'    # Cyan - for info/headers
YELLOW = '\033[93m'  # Yellow - for warnings/timing
RESET = '\033[0m'    # Reset - to return to default color

# Prompt user to enter the target IP address
target = input("Enter target IP: ") 

# Prompt user to enter how many ports to scan (e.g., 80 means ports 1-80)
number_of_ports = int(input("Enter number of ports to scan: "))

# Record the start time to calculate total scan duration later
start_time = datetime.now()

# Print a colored header showing which target is being scanned
print(f"{CYAN}[*] Starting port scan on {target} for ports 1-{number_of_ports}...{RESET}\n")

# Loop through ports 1 to number_of_ports to check their status
for port in range(1, number_of_ports + 1):
    # Create a new socket using IPv4 and TCP protocol
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Set timeout to 0.5 seconds so the script doesn't hang on unresponsive ports
    s.settimeout(0.5)
    
    # Try to connect to the target IP and current port
    # connect_ex() returns 0 if the connection succeeds (port is open)
    result = s.connect_ex((target, port))
    
    if result == 0:
        # Port is open: print in green and send a desktop notification
        print(f"{GREEN}[+] Port {port} is open{RESET}")
        notification.notify(title='Alert', message=f"Port {port} is open!") 
    else:
        # Port is closed: print in red
        print(f"{RED}[-] Port {port} is closed{RESET}")
    
    # Close the socket to free up resources
    s.close()

# Record the end time after the loop finishes
end_time = datetime.now()

# Calculate and display the total time taken for the scan in yellow
print(f"\n{YELLOW}[*] Scan completed in {end_time - start_time}{RESET}")

