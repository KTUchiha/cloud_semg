import asyncio
import psycopg2
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
from scipy.interpolate import interp1d
import numpy as np
from collections import Counter
import re
import os
# Initialize PostgreSQL connection
def init_connection():
    return psycopg2.connect(
        host=os.environ['POSTGRES_HOST'],
        database=os.environ['POSTGRES_DB'],
        user=os.environ['POSTGRES_USER'],
        password=os.environ['POSTGRES_PASSWORD']
    )
conn = init_connection()

# Fetch users from the database
def fetch_users():
    cursor = conn.cursor()
    cursor.execute("SELECT userid, first_name, last_name FROM users;")
    users = cursor.fetchall()
    cursor.close()
    return users

# Fetch sensor data for a specific user within a time window
async def fetch_sensor_data(conn, user_id, time_window):
    cursor = conn.cursor()
    time_threshold = (datetime.now() - timedelta(seconds=time_window / 1000)).isoformat()
    cursor.execute(f'''
        SELECT millis, sensor_a0, sensor_a1, sensor_a2, sensor_a3, sensor_a4, ts 
        FROM user_sensor 
        WHERE userid = {user_id}
        ORDER BY millis DESC
    ''')
    rows = cursor.fetchall()
    cursor.close()
    return rows

# Fetch gesture data for a specific user within a time window
async def fetch_gesture_data(conn, user_id, time_window):
    cursor = conn.cursor()
    time_threshold = (datetime.now() - timedelta(seconds=time_window / 1000)).isoformat()
    cursor.execute(f'''
        SELECT response, timestamp 
        FROM api_responses 
        WHERE userid = {user_id}
        ORDER BY timestamp DESC
    ''')
    rows = cursor.fetchall()
    cursor.close()
    return rows

# Interpolate sensor data for smooth plotting
def interpolate_data(df):
    new_millis = np.linspace(df['millis'].min(), df['millis'].max(), num=500)
    interpolated_df = pd.DataFrame({'millis': new_millis})
    
    for sensor in ['sensor_a0', 'sensor_a1', 'sensor_a2', 'sensor_a3', 'sensor_a4']:
        f = interp1d(df['millis'], df[sensor], kind='linear', fill_value='extrapolate')
        interpolated_df[sensor] = f(new_millis)
    
    return interpolated_df

def round_down(value, base=50):
    return base * (value // base)

def round_up(value, base=50):
    return base * ((value + base - 1) // base)

# Transform gesture data for plotting
def transform_gesture_data(gesture_data):
    def extract_predictions(s):
        match = re.search(r"\[(.*?)\]", s)
        if match:
            predictions_str = match.group(1)
            # Extract predictions as strings
            predictions = [x.strip().strip("'") for x in predictions_str.split(",")]
            return predictions
        return []

    parsed_data = []
    for row in gesture_data:
        predictions = extract_predictions(row[0])
        timestamp = pd.to_datetime(row[1])
        parsed_data.append((predictions, timestamp))

    transformed_data = []
    for predictions, timestamp in parsed_data:
        num_predictions = len(predictions)
        start_time = timestamp - timedelta(milliseconds=num_predictions)
        time_delta = timedelta(milliseconds=1)
        for i, prediction in enumerate(predictions):
            transformed_data.append((start_time + i * time_delta, prediction))

    df = pd.DataFrame(transformed_data, columns=['timestamp', 'prediction'])

    # Apply moving window manually to get the most frequent gesture
    window_size = 5
    if len(df) >= window_size:
        most_common_predictions = []
        for i in range(len(df)):
            if i < window_size:
                window_predictions = df['prediction'][:i+1]
            else:
                window_predictions = df['prediction'][i-window_size+1:i+1]
            most_common = Counter(window_predictions).most_common(1)[0][0]
            most_common_predictions.append(most_common)
        df['prediction'] = most_common_predictions

    return df[['timestamp', 'prediction']]

# Plot gesture data
def plot_gestures(gesture_df):
    fig = go.Figure()

    # Add scatter plot for gestures
    fig.add_trace(go.Scatter(
        x=gesture_df['timestamp'],
        y=gesture_df['prediction'],
        mode='markers+text',
        name='Gestures',
        text=gesture_df['prediction'],
        textposition='top center',
        textfont=dict(
            family="Arial",
            size=12,  # Adjusted for better readability
            color="black",
            weight='bold'
        ),
        marker=dict(size=10),
    ))

    # Rotate x-axis labels and adjust the step size
    fig.update_xaxes(tickangle=-45, nticks=20)  # Rotate labels by 45 degrees, reduce the number of ticks

    # Set the layout of the figure
    fig.update_layout(
        title='Classified Gestures Over Time',
        xaxis_title='Timestamp',
        yaxis_title='Prediction',
        template='plotly_white',
        yaxis=dict(range=[-1, 6]),  # Adjusted to include all gestures
        margin=dict(l=0, r=0, t=50, b=50),  # Adjust margins to provide more space
        height=400,  # Increased height for better spacing
    )

    return fig


# Plot sensor data
def plot_data(df, paused, sensors_to_display, show_interpolated, auto_y, manual_y_min, manual_y_max):
    if paused:
        return None

    if show_interpolated:
        df = interpolate_data(df)

    if auto_y:
        y_min = df[sensors_to_display].min().min()
        y_max = df[sensors_to_display].max().max()
        y_min_rounded = round_down(y_min, 50)
        y_max_rounded = round_up(y_max, 50)
    else:
        y_min_rounded = manual_y_min
        y_max_rounded = manual_y_max

    fig = go.Figure()
    for sensor in sensors_to_display:
        fig.add_trace(go.Scatter(x=df['millis'], y=df[sensor], mode='lines', name=sensor))

    fig.update_layout(
        title='Real-time Sensor Data and Classified Gestures',
        xaxis_title='Milliseconds since start',
        yaxis_title='Sensor Value',
        yaxis=dict(range=[y_min_rounded, y_max_rounded]),
        template='plotly_white'
    )
    
    return fig

# Main async function
async def main():
    st.set_page_config(layout="wide")  # Set layout to wide to use the entire screen width
    st.markdown('### Real-time Gesture Classification')
    users = fetch_users()
    user_options = {f"{user[1]} {user[2]}": user[0] for user in users}
    selected_user_name = st.selectbox("Select User", list(user_options.keys()), index=0)
    selected_user_id = user_options[selected_user_name]

    col1, col2 = st.columns(2)
    with col1:
        sensor_fig = st.empty()
    with col2:
        gesture_fig = st.empty()

    settings_expander = st.expander("Settings", expanded=True)
    with settings_expander:
        col1, col2, col3 = st.columns(3)
        with col1:
            paused = st.checkbox('Pause')
        with col2:
            show_interpolated = st.checkbox('Show Interpolated Data', value=False)
        with col3:
            time_window = st.slider('Time Window (ms)', min_value=10, max_value=10000, value=10000, step=10)

        auto_y = st.checkbox('Auto Y-Axis Scaling', value=True)
        if not auto_y:
            manual_y_min = st.number_input('Manual Y-Axis Min', value=0)
            manual_y_max = st.number_input('Manual Y-Axis Max', value=1000)
        else:
            manual_y_min = None
            manual_y_max = None

        st.subheader('Select Sensors to Display')
        sensor_cols = st.columns(5)
        sensors = ['sensor_a0', 'sensor_a1', 'sensor_a2', 'sensor_a3', 'sensor_a4']
        sensor_checkboxes = {sensor: sensor_cols[i].checkbox(sensor, value=True) for i, sensor in enumerate(sensors)}

        sensors_to_display = [sensor for sensor, checked in sensor_checkboxes.items() if checked]

        sensor_data = await fetch_sensor_data(conn, selected_user_id, time_window)
        gesture_data = await fetch_gesture_data(conn, selected_user_id, time_window)
        
        sensors_to_display = [sensor for sensor, checked in sensor_checkboxes.items() if checked]
        df = pd.DataFrame(sensor_data, columns=['millis', 'sensor_a0', 'sensor_a1', 'sensor_a2', 'sensor_a3', 'sensor_a4', 'ts'])
        df = df.sort_values(by='millis')
        
        gesture_df = transform_gesture_data(gesture_data)

        sensor_fig.plotly_chart(plot_data(df, paused, sensors_to_display, show_interpolated, auto_y, manual_y_min, manual_y_max), use_container_width=True)
        gesture_fig.plotly_chart(plot_gestures(gesture_df), use_container_width=True)
        


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
