import asyncio
import requests
import psycopg2
from nats.aio.client import Client as NATS
from datetime import datetime

NATS_SERVER = "nats://127.0.0.1:4222"
NATS_USER = "XXXXXXX" # Your username here
NATS_PASSWORD = "XXXXXXX" # Your password here
NATS_TOPIC = "sensor.data"
API_URL = "http://127.0.0.1:8000/predict"
BATCH_SIZE = 64

# PostgreSQL connection parameters
POSTGRES_HOST = "localhost"
POSTGRES_DB = "sensordb"
POSTGRES_USER = "XXXXXXX"
POSTGRES_PASSWORD = "XXXXXXXX"  # Your password here

# List to store received data
data_list = []

# Store the API response in the PostgreSQL database
async def store_api_response(userid, response):
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO api_responses (userid, response, timestamp)
            VALUES (%s, %s, %s)
        ''', (userid, response, timestamp))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Failed to store API response in PostgreSQL. Error: {e}")

# Function to process the sensor data and make API call
async def process_sensor_data():
    try:
        # Extract the user ID from the first entry (assuming it's the same for all entries in the batch)
        userid = data_list[0]["userid"]

        # Sort data_list by millis
        sorted_data = sorted(data_list, key=lambda x: x["millis"])

        # Extract the first 4 sensor values for each entry
        sorted_sensor_values = [entry["sensor_values"][:4] for entry in sorted_data]

        # Prepare the payload for the API call
        payload = {
            "userid": userid,
            "data": sorted_sensor_values
        }

        try:
            # Send the POST request to the /predict endpoint
            response = requests.post(API_URL, json=payload)
            response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)

            # Print the response
            print(datetime.now().isoformat(), response.json())

            # Store the response in the PostgreSQL database
            await store_api_response(userid, str(response.json()))

        except requests.exceptions.RequestException as e:
            # Handle any exceptions that occur during the request
            print(f"Failed to send request to the API. Error: {e}")
            await store_api_response(userid, f"Request failed: {e}")

    except Exception as e:
        print(f"Failed to process sensor data. Error: {e}")

# Callback function to handle messages from NATS
async def message_handler(msg):
    try:
        data_str = msg.data.decode()
        data = eval(data_str)  # Use json.loads for a more secure conversion if the data is JSON formatted
        data_list.append(data)

        # Process data if we have accumulated enough messages
        if len(data_list) >= BATCH_SIZE:
            await process_sensor_data()
            data_list.clear()
    except Exception as e:
        print(f"Failed to handle message. Error: {e}")

# Main function to subscribe to NATS topic and process data
async def main():
    nc = NATS()

    # Connect to the NATS server with authentication
    await nc.connect(
        servers=[NATS_SERVER],
        user=NATS_USER,
        password=NATS_PASSWORD
    )

    # Subscribe to the NATS topic
    await nc.subscribe(NATS_TOPIC, cb=message_handler)

    # Keep the subscriber running
    try:
        while True:
            await asyncio.sleep(0.2)  # Sleep for a second and keep checking
    finally:
        await nc.drain()

if __name__ == "__main__":
    asyncio.run(main())
