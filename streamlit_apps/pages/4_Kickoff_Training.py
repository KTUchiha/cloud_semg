import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
import cv2
import numpy as np
import tempfile
import subprocess
import os
# Initialize database connection
def init_connection():
    return psycopg2.connect(
        host=os.environ['POSTGRES_HOST'],
        database=os.environ['POSTGRES_DB'],
        user=os.environ['POSTGRES_USER'],
        password=os.environ['POSTGRES_PASSWORD']
    )

# Initialize connection
conn = init_connection()

# Function to fetch users
def fetch_users():
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users;")
    return cursor.fetchall()

# Function to fetch training metadata for a user
def fetch_training_metadata_for_user(user_id):
    cursor = conn.cursor()
    query = """
    SELECT * FROM user_gesture_trainingmetadata WHERE userid = %s;
    """
    cursor.execute(query, (user_id,))
    rows = cursor.fetchall()
    return rows

# Function to fetch raw sensor data based on userid, start_time, and end_time
def fetch_sensor_data(user_id, start_time, end_time):
    cursor = conn.cursor()
    
    user_id = int(user_id)
    start_time = pd.Timestamp(start_time).to_pydatetime()
    end_time = pd.Timestamp(end_time).to_pydatetime()
    
    query = """
    SELECT * FROM user_sensor 
    WHERE userid = %s AND ts BETWEEN %s AND %s;
    """
    cursor.execute(query, (user_id, start_time, end_time))
    rows = cursor.fetchall()
    return rows


# Function to run the training job in the background using subprocess
def submit_job_in_background(job_id):
    try:
        # Construct the command
        command = ["python3", "../ml_model/TrainMLJob.py", str(job_id)]
        
        # Run the command using subprocess in the background
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        
        st.success(f"Training job {job_id} processing has begun")

    except Exception as e:
        st.error(f"An error occurred while submitting the job: {e}")

# Function to fetch video frames for the selected session
def fetch_video_frames(user_id, start_time, end_time):
    cursor = conn.cursor()
    
    query = """
    SELECT video_frame, "timestamp" FROM user_video 
    WHERE userid = %s AND "timestamp" BETWEEN %s AND %s;
    """
    cursor.execute(query, (user_id, start_time, end_time))
    rows = cursor.fetchall()
    return rows

# Function to convert rows to a pandas DataFrame
def convert_to_dataframe(rows, columns):
    return pd.DataFrame(rows, columns=columns)

def save_frames_to_video(frames, frame_size, fps=30):
    import tempfile
    import cv2

    temp_video_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    video_path = temp_video_file.name

    # Initialize the VideoWriter with H.264 codec
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # H.264 codec
    out = cv2.VideoWriter(video_path, fourcc, fps, frame_size)

    for frame_bgr in frames:
        out.write(frame_bgr)  # No need to convert to RGB when writing

    out.release()
    return video_path


# Function to kick off training process
def kick_off_training(selected_data):
    conn = init_connection()
    cursor = conn.cursor()
    
    try:
        # Convert numpy types to native Python types
        user_id = int(selected_data.iloc[0]['userid'])  # Assuming all rows have the same user_id
        num_samples = int(len(selected_data))
        
        insert_job_query = """
        INSERT INTO training_job_schedule (userid, job_status, num_samples)
        VALUES (%s, %s, %s) RETURNING job_id;
        """
        cursor.execute(insert_job_query, (user_id, 'scheduled', num_samples))
        job_id = cursor.fetchone()[0]
        
        # Insert associated training metadata into job_training_metadata
        insert_metadata_query = """
        INSERT INTO job_training_metadata (job_id, training_metadata_id)
        VALUES (%s, %s);
        """
        for _, row in selected_data.iterrows():
            training_metadata_id = int(row['training_metadata_id'])
            cursor.execute(insert_metadata_query, (job_id, training_metadata_id))
        
        # Commit the transaction
        conn.commit()
        st.success(f"Training job {job_id} has been scheduled successfully!")
        submit_job_in_background(job_id)
        st.success(f"Training job {job_id} processing has begun ")




    except Exception as e:
        conn.rollback()
        st.error(f"An error occurred while scheduling the training job: {str(e)}")
    finally:
        cursor.close()
        conn.close()



# Streamlit UI
st.title("Review and Kick Off Gesture Training")

# Fetch all users
users = fetch_users()

# Create a dropdown to select a user
user_options = [(f"{user[1]} {user[2]}", user[0]) for user in users]  # (user_full_name, user_id)
user_selected = st.selectbox("Select User", user_options, format_func=lambda x: x[0])

if user_selected:
    user_id = user_selected[1]

    # Fetch training metadata for the selected user
    training_data = fetch_training_metadata_for_user(user_id)
    
    if training_data:
        training_columns = ["training_metadata_id", "userid", "gestureid", "timestamp", "sample_number", "status", "start_time", "end_time"]
        df = convert_to_dataframe(training_data, training_columns)
        st.subheader("Training Metadata for User")
        st.dataframe(df)

        if 'selected_rows' not in st.session_state:
            st.session_state.selected_rows = [False] * len(df)

        col1, col2 = st.columns(2)
        if col1.button("Select All"):
            st.session_state.selected_rows = [True] * len(df)
        if col2.button("Unselect All"):
            st.session_state.selected_rows = [False] * len(df)

        st.subheader("Select Training Sessions")
        cols = st.columns(5)  # Create 5 columns
        selected_rows = []
        for idx, row in df.iterrows():
            col = cols[idx % 5]
            if col.checkbox(f"Session {row['training_metadata_id']}", key=idx, value=st.session_state.selected_rows[idx]):
                selected_rows.append(idx)
                st.session_state.selected_rows[idx] = True
            else:
                st.session_state.selected_rows[idx] = False

        if selected_rows:
            selected_data = df.loc[selected_rows]
            st.write("Selected Data for Training")
            st.dataframe(selected_data)

            # Dropdown to select one session for displaying sensor data
            st.subheader("Select a Session to View Raw Sensor Data")
            session_selected = st.selectbox("Select Session", selected_data['training_metadata_id'].unique())

            if session_selected:
                session_data = selected_data[selected_data['training_metadata_id'] == session_selected].iloc[0]
                start_time = session_data['start_time']
                end_time = session_data['end_time']

                # Fetch sensor data for the selected session
                sensor_data = fetch_sensor_data(session_data['userid'], start_time, end_time)
                if sensor_data:
                    sensor_columns = ["id", "userid", "millis", "sensor_a0", "sensor_a1", "sensor_a2", "sensor_a3", "sensor_a4", "timestamp"]
                    sensor_df = convert_to_dataframe(sensor_data, sensor_columns)
                    
                    st.subheader(f"Raw Sensor Data for Session {session_selected}")
                    fig = px.line(sensor_df, x='timestamp', y=['sensor_a0', 'sensor_a1', 'sensor_a2', 'sensor_a3', 'sensor_a4'],
                                  labels={'timestamp': 'Time', 'value': 'Sensor Values'},
                                  title=f"Sensor Data for Session {session_selected}")
                    st.plotly_chart(fig)
                else:
                    st.write("No sensor data found for this session.")

                # Fetch and display video frames
                st.subheader(f"Video for Session {session_selected}")
                video_frames = fetch_video_frames(int(session_data['userid']), start_time, end_time)
                if video_frames:
                    st.write(f"Found {len(video_frames)} video frames.")
                    frame_size = (640, 480)  # You can modify this based on your video dimensions
                    frames = []
                    for frame, frame_timestamp in video_frames:
                        img_np = np.frombuffer(frame, dtype=np.uint8)
                        img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
                        #img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                        frames.append(img)
                    
                    # Save frames to a video file
                    video_file_path = save_frames_to_video(frames, frame_size)
                    
                    # Display video in Streamlit
                    st.video(video_file_path)
                else:
                    st.write("No video frames found for this session.")
            
            if st.button("Kick Off Training"):
                kick_off_training(selected_data)
    else:
        st.write("No training data found for this user.")
