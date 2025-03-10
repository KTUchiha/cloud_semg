import asyncio
import socket
import random
import time

DEST_IP = "XX.XX.XX.XX"
DEST_PORT = 8081
PACKET_RATE = 50  # packets per second
PACKET_INTERVAL = 1.0 / PACKET_RATE

async def send_udp_packets():
    # Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    userid = 2
    packet_count = 0

    # Track the last time we printed
    last_print_time = time.time()

    while True:
        # Get current UTC time in milliseconds since epoch
        elapsed_ms = int(time.time() * 1000)

        # Generate some random sensor values for demonstration
        sensor_values = [
            round(random.uniform(0, 100), 2),  # sensor_A0
            round(random.uniform(0, 100), 2),  # sensor_A1
            round(random.uniform(0, 100), 2),  # sensor_A2
            round(random.uniform(0, 100), 2),  # sensor_A3
            round(random.uniform(0, 100), 2)   # sensor_A4
        ]

        # Construct the comma-separated packet
        # Format: userid,millis,sensorA0,sensorA1,sensorA2,sensorA3,sensorA4
        data_str = f"{userid},{elapsed_ms}," + ",".join(map(str, sensor_values))
        data_bytes = data_str.encode("utf-8")

        # Send the UDP packet
        sock.sendto(data_bytes, (DEST_IP, DEST_PORT))
        packet_count += 1

        # Print once per second to reduce console spam
        current_time = time.time()
        if current_time - last_print_time >= 1.0:
            print(f"Sent packet #{packet_count}: {data_str}")
            last_print_time = current_time

        # Sleep to maintain ~50 packets per second
        await asyncio.sleep(PACKET_INTERVAL)

async def main():
    await send_udp_packets()

if __name__ == "__main__":
    asyncio.run(main())
