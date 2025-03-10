import requests
import psycopg2
import pandas as pd
import json

# Database connection
def get_db_connection():
    return psycopg2.connect(
        host="localhost",
        database="sensordb",
        user="kaavya",
        password=""  # Your password here
    )

# Function to fetch data from user_sensor table in batches
def fetch_sensor_data_batches(user_id, batch_size=64):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
    SELECT sensor_a0, sensor_a1, sensor_a2, sensor_a3, sensor_a4
    FROM user_sensor
    WHERE userid = %s
    ORDER BY ts ASC
    LIMIT %s OFFSET %s;
    """

    offset = 0
    while True:
        cursor.execute(query, (user_id, batch_size, offset))
        rows = cursor.fetchall()

        if not rows:
            break

        yield rows
        offset += batch_size

    cursor.close()
    conn.close()

# Function to prepare data for prediction and make API requests
def predict_batches(user_id, api_url):
    for batch in fetch_sensor_data_batches(user_id):
        # Prepare data in the format expected by the API
        data = {
            "userid": user_id,
            "data": [list(row) for row in batch]  # Converting tuples to lists
        }

        # Make POST request to the API
        #print(data)
        response = requests.post(api_url, json=data)

        if response.status_code == 200:
            predictions = response.json().get("predictions", [])
            print(f"Batch predictions: {predictions}")
            print(f"PREDICTIONS:{len(predictions)},ACTUALS:{len(batch)} ")
        else:
            print(f"Error: {response.status_code} - {response.text}")

# Example usage
api_url = "http://localhost:8000/predict"  # Replace with your API URL
user_id = 1
predict_batches(user_id, api_url)
