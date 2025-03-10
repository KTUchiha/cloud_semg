import asyncio
import socket
from datetime import datetime
import sys
import psycopg2
from nats.aio.client import Client as NATS

# Initialize NATS client
async def initialize_nats():
    nc = NATS()
    await nc.connect(
        servers=["nats://127.0.0.1:4222"],
        user="XXXXXX",
        password="XXXXXXX"
    )
    return nc

# Initialize PostgreSQL database connection
def initialize_db():
    conn = psycopg2.connect(
        host="localhost",       # Adjust as necessary
        database="sensordb",
        user="XXXXXXX",
        password="XXXXXXXX"
    )
    return conn

# Store sensor data in the PostgreSQL database
def store_data(conn, userid, millis, sensor_values, ts):
    cursor = conn.cursor()
    try:
        # Ensure sensor_values list has 5 elements, filling missing values with 0
        sensor_values += [0] * (5 - len(sensor_values))
        
        cursor.execute('''
            INSERT INTO user_sensor (userid, millis, sensor_a0, sensor_a1, sensor_a2, sensor_a3, sensor_a4, ts)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (userid, millis, *sensor_values, ts))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Failed to store data: {e}")
    finally:
        cursor.close()

# Handle incoming UDP data
async def handle_data(conn, data, addr, nc):
    try:
        # Assuming the data is sent as a comma-separated string: userid,millis,sensor_A0,sensor_A1,sensor_A2,sensor_A3,sensor_A4
        data_str = data.decode().strip()
        values = data_str.split(',')
        
        userid = int(values[0])
        millis = int(values[1])
        sensor_values = [float(value) for value in values[2:]]
        ts = datetime.now().isoformat()  # Calculate timestamp when packet is received

        # Store data in PostgreSQL
        store_data(conn, userid, millis, sensor_values, ts)
        print(f"Stored data from {addr}: {data_str}")
        
        # Publish data to NATS
        message = {
            "userid": userid,
            "millis": millis,
            "sensor_values": sensor_values,
            "timestamp": ts
        }
        await nc.publish("sensor.data", str(message).encode())
        print(f"Published data to NATS: {message}")
    except Exception as e:
        print(f"Failed to handle data from {addr}: {data}. Error: {e}")

# Function to get the IP address of the Wi-Fi LAN
def get_ip_address():
    try:
        # Connect to an external host to find out the network interface IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
        s.close()
        return ip_address
    except Exception as e:
        return f"Unable to get IP address: {e}"

# Main UDP server function
async def udp_server(host, port, conn, nc):
    loop = asyncio.get_event_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    sock.setblocking(False)

    ip_address = get_ip_address()
    print(f"Wi-Fi LAN IP Address: {ip_address}")
    print(f"UDP Server started on {ip_address}:{port}")

    while True:
        try:
            data, addr = await loop.run_in_executor(None, sock.recvfrom, 1024)
            asyncio.create_task(handle_data(conn, data, addr, nc))
        except BlockingIOError:
            await asyncio.sleep(0.1)  # Adjust the sleep time as needed

# Main entry point
async def main():
    conn = initialize_db()  # Initialize the PostgreSQL connection
    nc = await initialize_nats()  # Initialize the NATS client
    await udp_server('0.0.0.0', 8081, conn, nc)

if __name__ == "__main__":
    asyncio.run(main())
