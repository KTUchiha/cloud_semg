import psycopg2
import random
from datetime import datetime, timedelta
import os
# Initialize database connection
def init_connection():
    return psycopg2.connect(
        host=os.environ['POSTGRES_HOST'],
        database=os.environ['POSTGRES_DB'],
        user=os.environ['POSTGRES_USER'],
        password=os.environ['POSTGRES_PASSWORD']
    )

# Function to insert a single sensor data entry into the user_sensor table
def insert_sensor_data(cursor, userid, millis, sensors, timestamp):
    query = """
    INSERT INTO user_sensor (userid, millis, sensor_a0, sensor_a1, sensor_a2, sensor_a3, sensor_a4, ts) 
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(query, (userid, millis, sensors[0], sensors[1], sensors[2], sensors[3], sensors[4], timestamp))

# Function to generate 50Hz sample data for given time intervals
def generate_and_insert_data(conn, userid, start_time, end_time):
    cursor = conn.cursor()
    
    # Calculate the duration in seconds and total samples (50 samples per second)
    total_seconds = (end_time - start_time).total_seconds()
    total_samples = int(total_seconds * 50)  # 50Hz data

    # Simulate sensor data for sensors A0 to A5 (6 sensors)
    for i in range(total_samples):
        # Generate random values for each sensor (you can replace this with real data)
        sensors = [random.uniform(0, 1) for _ in range(5)]
        
        # Calculate the timestamp and millis for each sample
        timestamp = start_time + timedelta(seconds=i / 50.0)  # 50Hz = 1/50th of a second
        millis = int(i * (1000 / 50))  # Millis per sample (for 50Hz, 20ms per sample)
        
        # Insert data into the database
        insert_sensor_data(cursor, userid, millis, sensors, timestamp)
    
    # Commit the transaction to save the data
    conn.commit()
    cursor.close()
input_string = """
2024-08-26 17:52:20-07:00	2024-08-26 17:52:25-07:00
2024-08-26 17:52:25-07:00	2024-08-26 17:52:27-07:00
2024-08-26 17:52:27-07:00	2024-08-26 17:52:32-07:00
2024-08-26 17:52:32-07:00	2024-08-26 17:52:35-07:00
2024-08-26 17:52:35-07:00	2024-08-26 17:52:40-07:00
2024-08-26 17:52:42-07:00	2024-08-26 17:52:47-07:00
2024-08-26 17:52:47-07:00	2024-08-26 17:52:50-07:00
2024-08-26 17:52:50-07:00	2024-08-26 17:52:55-07:00
2024-08-26 17:52:55-07:00	2024-08-26 17:52:57-07:00
2024-08-26 17:52:57-07:00	2024-08-26 17:53:02-07:00
2024-08-26 17:53:05-07:00	2024-08-26 17:53:10-07:00
2024-08-26 17:53:10-07:00	2024-08-26 17:53:12-07:00
2024-08-26 17:52:40-07:00	2024-08-26 17:52:42-07:00
2024-08-26 17:52:55-07:00	2024-08-26 17:52:57-07:00
2024-08-26 17:53:02-07:00	2024-08-26 17:53:05-07:00
2024-08-26 17:53:20-07:00	2024-08-26 17:53:25-07:00
2024-08-26 17:53:25-07:00	2024-08-26 17:53:27-07:00
2024-08-26 17:53:32-07:00	2024-08-26 17:53:35-07:00
2024-08-26 17:53:12-07:00	2024-08-26 17:53:17-07:00
2024-08-26 17:53:40-07:00	2024-08-26 17:53:42-07:00
2024-08-26 17:53:42-07:00	2024-08-26 17:53:47-07:00
2024-08-26 17:53:47-07:00	2024-08-26 17:53:50-07:00
2024-08-26 17:53:50-07:00	2024-08-26 17:53:55-07:00
2024-08-26 17:53:55-07:00	2024-08-26 17:53:57-07:00
2024-08-26 17:53:27-07:00	2024-08-26 17:53:32-07:00
2024-08-26 17:53:32-07:00	2024-08-26 17:53:35-07:00
2024-08-26 17:53:35-07:00	2024-08-26 17:53:40-07:00
2024-08-26 17:53:17-07:00	2024-08-26 17:53:20-07:00
2024-08-26 17:53:57-07:00	2024-08-26 17:54:02-07:00
2024-08-26 17:54:05-07:00	2024-08-26 17:54:10-07:00
2024-08-26 17:54:10-07:00	2024-08-26 17:54:12-07:00
2024-08-26 17:54:10-07:00	2024-08-26 17:54:12-07:00
2024-08-26 17:54:02-07:00	2024-08-26 17:54:05-07:00
"""

# Split the input string by lines
lines = input_string.strip().split('\n')

# Create a list of tuples
time_intervals = [(line.split("\t")[0], line.split("\t")[1]) for line in lines]

# Connect to the database
conn = init_connection()

# Loop through each interval and generate data for user_id=1
for start_str, end_str in time_intervals:
    start_time = datetime.strptime(start_str,  "%Y-%m-%d %H:%M:%S%z")
    end_time = datetime.strptime(end_str,  "%Y-%m-%d %H:%M:%S%z")
    
    # Generate and insert data for the given interval
    generate_and_insert_data(conn, userid=1, start_time=start_time, end_time=end_time)

# Close the database connection
conn.close()
