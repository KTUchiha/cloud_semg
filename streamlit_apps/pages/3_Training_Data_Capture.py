import streamlit as st
from streamlit_webrtc import webrtc_streamer
import av
import cv2
import time
from datetime import datetime, timedelta
import psycopg2
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

# Initialize database connection
def init_connection():
    return psycopg2.connect(
        host="localhost",       # Adjust as necessary
        database="sensordb",
        user="kaavya",
        password="sEMG1234"
    )

# Initialize connection
conn = init_connection()

# Function to insert the timing plan into the database with start and end times
def insert_timing_plan_async(user_id, gesture_id, timestamp, sample_number, status, start_time, end_time):
    try:
        cursor = conn.cursor()
        query = """
        INSERT INTO public.user_gesture_trainingmetadata (userid, gestureid, "timestamp", sample_number, status, start_time, end_time) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (user_id, gesture_id, timestamp, sample_number, status, start_time, end_time))
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"Error inserting timing plan: {e}")

# Function to insert video frames into the database asynchronously
def insert_frame_async(user_id, frame_bytes):
    try:
        cursor = conn.cursor()
        query = """
        INSERT INTO public.user_video (userid, video_frame, "timestamp") 
        VALUES (%s, %s, CURRENT_TIMESTAMP)
        """
        cursor.execute(query, (user_id, frame_bytes))
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"Error inserting frame: {e}")

# Convert frame to byte array
def frame_to_bytes(frame):
    is_success, buffer = cv2.imencode(".jpg", frame)
    if not is_success:
        raise Exception("Failed to convert frame to bytes")
    return buffer.tobytes()

# Thread pool for asynchronous insertion
executor = ThreadPoolExecutor()

# Function to fetch all users
def fetch_users():
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users;")
    return cursor.fetchall()

# Function to fetch user gestures for a specific user
def fetch_gestures(userid):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_gestures WHERE userid = %s;", (userid,))
    return cursor.fetchall()

# Timing plan generation function and insert into DB with start and end time
def create_timing_plan_with_active_pause(gesture_ids, samples_per_gesture, seconds_for_gesture_capture, seconds_for_rest, user_id):
    plan_data = []
    current_time = datetime.now()

    for gesture_id in gesture_ids:
        for sample_num in range(1, samples_per_gesture + 1):
            start_time = current_time
            # Rest entry
            plan_data.append({
                'timestamp': current_time,
                'gesture': int(gesture_id),
                'sample number': int(sample_num),
                'status': 'REST PERIOD'
            })
            executor.submit(insert_timing_plan_async, user_id, gesture_id, current_time, sample_num, 'REST PERIOD', start_time, current_time + timedelta(seconds=seconds_for_rest))
            current_time += timedelta(seconds=seconds_for_rest)

            # Active entry
            start_time = current_time
            plan_data.append({
                'timestamp': current_time,
                'gesture': int(gesture_id),
                'sample number': int(sample_num),
                'status': 'MAKE GESTURE'
            })
            executor.submit(insert_timing_plan_async, user_id, gesture_id, current_time, sample_num, 'MAKE GESTURE', start_time, current_time + timedelta(seconds=seconds_for_gesture_capture))
            current_time += timedelta(seconds=seconds_for_gesture_capture)

        # Completion entry for gesture
        plan_data.append({
            'timestamp': current_time,
            'gesture': int(gesture_id),
            'sample number': int(sample_num),
            'status': 'SAMPLE COMPLETE'
        })
        executor.submit(insert_timing_plan_async, user_id, gesture_id, current_time, sample_num, 'SAMPLE COMPLETE', start_time, current_time)

    return pd.DataFrame(plan_data)

# Callback function to overlay the timing plan status on the video frame and save frame to DB
def video_frame_callback(frame):
    img = frame.to_ndarray(format="bgr24")
    current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    cv2.putText(img, current_timestamp, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2, cv2.LINE_AA)

    try:
        if 'timing_plan' not in st.session_state:
            cv2.putText(img, "NO TIMING PLAN", (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2, cv2.LINE_AA)
            st.session_state.timing_plan = create_timing_plan_with_active_pause(
                selected_gestures, samples_per_gesture, seconds_per_gesture_capture, seconds_for_rest, selected_user_id)
        else:
            timing_plan = st.session_state.timing_plan
            current_row = timing_plan.loc[(timing_plan['timestamp'] <= current_timestamp)].tail(1)
            if len(current_row) > 0:
                status = current_row['status'].values[0]
                if status != 'SAMPLE COMPLETE':
                    gesture = current_row['gesture'].values[0]
                    ts = pd.to_datetime(current_row['timestamp'].values[0])
                    sample_num = current_row['sample number'].values[0]
                    wseconds = seconds_per_gesture_capture if status == 'MAKE GESTURE' else seconds_for_rest
                    wait_time = ((ts + timedelta(seconds=wseconds)) - datetime.now()).seconds
                    cv2.putText(img, f"GESTURE ID: {gesture}", (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
                    cv2.putText(img, f"SAMPLE    : {sample_num}", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
                    cv2.putText(img, f"ACTION    : {status}", (10, 160), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
                    cv2.putText(img, f"WAIT TIME : {wait_time}", (10, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)

                    # Convert frame to bytes and insert it into the DB asynchronously
                    frame_bytes = frame_to_bytes(img)
                    executor.submit(insert_frame_async, selected_user_id, frame_bytes)

                else:
                    cv2.putText(img, "SAMPLE COLLECTION COMPLETED", (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
    except:
        cv2.putText(img, "Error checking for timing plan", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

    return av.VideoFrame.from_ndarray(img, format="bgr24")


# Streamlit UI for managing gesture data capture
st.title("Personalized Gesture Recognition System: Training Data Capture")

# Fetch users from the database
users = fetch_users()
users_df = [(user[0], f"{user[1]} {user[2]}") for user in users]  # Assuming user[1] = first name, user[2] = last name

# Separate the names and user IDs
user_ids = [user[0] for user in users]
user_names = [f"{user[1]} {user[2]}" for user in users]

# Dropdown to select user (Only show the name in the dropdown)
st.subheader("Select User")
selected_user_name = st.selectbox("User", user_names)

# Find the corresponding user ID
selected_user_id = user_ids[user_names.index(selected_user_name)]

# Number of samples per gesture and seconds per gesture inputs
col1, col2 = st.columns(2)
samples_per_gesture = col1.number_input("Samples per Gesture", min_value=1, value=5)
seconds_per_gesture_capture = col2.number_input("Seconds per Gesture", min_value=0.5, value=2.5, step=0.1)
seconds_for_rest = col2.number_input("Seconds for Rest", min_value=0.5, value=5.0, step=0.5)

# Display user gestures for the selected user
user_gestures = fetch_gestures(selected_user_id)
gestures_df = [(gesture[0], gesture[2]) for gesture in user_gestures]  # Assuming gesture[2] = gesture description

# Start data collection button
st.session_state.gesture_ids = [g[0] for g in gestures_df]
st.session_state.samples_per_gesture = samples_per_gesture
st.session_state.seconds_per_gesture_capture = seconds_per_gesture_capture
st.session_state.seconds_for_rest = seconds_for_rest
st.write(f"Collect Training Data for the following gestures: {','.join([g[1] for g in gestures_df])}")
selected_gestures = st.multiselect(f'Gestures Enabled for Training Data Collection for {selected_user_name}:',
                                   st.session_state.gesture_ids, default=st.session_state.gesture_ids)

# Display the video stream
st.subheader("Webcam Video Stream (for Gesture Recording)")
webrtc_streamer(key="training_stream",
                rtc_configuration={  # Add this config
        "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
                        },
                 video_frame_callback=video_frame_callback)