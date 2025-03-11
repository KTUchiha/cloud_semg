import socket
import time
import random
from datetime import datetime
import os
# Server address and port
UDP_IP = "127.0.0.1"  # Replace with the actual IP address of the UDP server
UDP_IP="74.208.201.225"
UDP_PORT = 8081

# Define the user ID and number of sensors
USER_ID = 1
NUM_SENSORS = 5
MESSAGE_INTERVAL = 1.0 / 50.0  # Interval for 50Hz

def generate_sensor_values(num_sensors):
    """Generate a list of random sensor values."""
    return [random.uniform(0, 1) for _ in range(num_sensors)]

def main():
    # Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    millis = 0

    try:
        while True:
            # Generate random sensor values
            sensor_values = generate_sensor_values(NUM_SENSORS)
            
            # Get the current timestamp
            timestamp = datetime.now().isoformat()

            # Create the message string: userid,millis,timestamp,sensor_A0,sensor_A1,...,sensor_A4
            message = f"{USER_ID},{millis}," + ",".join(map(str, sensor_values))
            
            # Send the message to the UDP server
            sock.sendto(message.encode(), (UDP_IP, UDP_PORT))
            print(f"Sent: {message}")
            
            # Increment the millis counter (simulate time progression)
            millis += 20  # Each loop iteration corresponds to 20ms

            # Wait for the next message interval
            time.sleep(MESSAGE_INTERVAL)

    except KeyboardInterrupt:
        print("UDP client stopped.")
    finally:
        sock.close()

if __name__ == "__main__":
    main()
