import streamlit as st
import psycopg2
import pandas as pd

# Set up a connection to the PostgreSQL database
def init_connection():
    return psycopg2.connect(
        host="localhost",       # Adjust as necessary
        database="sensordb",
        user="kaavya",
        password="sEMG1234"
    )

# Initialize connection
conn = init_connection()
cursor = conn.cursor()

def delete_gesture(gestureid):
    query = "DELETE FROM user_gestures WHERE gestureid = %s;"
    cursor.execute(query, (gestureid,))
    conn.commit()

# Function to fetch all users
def fetch_users():
    cursor.execute("SELECT * FROM users;")
    return cursor.fetchall()

# Function to fetch user gestures for a specific user
def fetch_gestures(userid):
    cursor.execute("SELECT * FROM user_gestures WHERE userid = %s;", (userid,))
    return cursor.fetchall()

# Function to create a gesture for a user
def create_gesture(userid, description, sensors):
    query = """INSERT INTO user_gestures (userid, gesture_description, sensor_a0_used, sensor_a1_used, 
               sensor_a2_used, sensor_a3_used, sensor_a4_used, sensor_a0_purpose, sensor_a1_purpose, 
               sensor_a2_purpose, sensor_a3_purpose, sensor_a4_purpose)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);"""
    cursor.execute(query, (userid, description, sensors['sensor_a0_used'], sensors['sensor_a1_used'], 
                           sensors['sensor_a2_used'], sensors['sensor_a3_used'], sensors['sensor_a4_used'], 
                           sensors['sensor_a0_purpose'], sensors['sensor_a1_purpose'], sensors['sensor_a2_purpose'], 
                           sensors['sensor_a3_purpose'], sensors['sensor_a4_purpose']))
    conn.commit()

# Streamlit Interface
st.title("Gesture Management")

# Fetch users and show drop-down with First Name + Last Name
users = fetch_users()
users_df = pd.DataFrame(users, columns=["UserID", "First Name", "Last Name", "Email", "Description"])
users_df["Full Name"] = users_df["First Name"] + " " + users_df["Last Name"]

# Select user by Full Name
selected_user = st.selectbox("Select User for Gestures", users_df["Full Name"])

# Find the UserID of the selected user
selected_user_row = users_df[users_df["Full Name"] == selected_user]
selected_user_id = int(selected_user_row["UserID"].values[0])

if selected_user_id:
    # Create gesture with sensor inputs
    with st.form("create_gesture"):
        st.subheader(f"Create Gesture for {selected_user}")
        
        # Gesture description
        gesture_description = st.text_input("Gesture Description")
  
        
        # Create checkboxes and corresponding text inputs
        col1, col2 = st.columns(2)
        sensor_a0_used = col1.checkbox("Use Sensor A0")
        sensor_a0_purpose = col2.text_input("Sensor A0 Description")
        col1, col2 = st.columns(2)
        sensor_a1_used = col1.checkbox("Use Sensor A1")
        sensor_a1_purpose = col2.text_input("Sensor A1 Description")
        col1, col2 = st.columns(2)
        sensor_a2_used = col1.checkbox("Use Sensor A2")
        sensor_a2_purpose = col2.text_input("Sensor A2 Description")
        col1, col2 = st.columns(2)
        sensor_a3_used = col1.checkbox("Use Sensor A3")
        sensor_a3_purpose = col2.text_input("Sensor A3 Description")
        col1, col2 = st.columns(2)
        sensor_a4_used = col1.checkbox("Use Sensor A4")
        sensor_a4_purpose = col2.text_input("Sensor A4 Description")

        # Collect all the sensor data
        sensors = {
            'sensor_a0_used': sensor_a0_used,
            'sensor_a1_used': sensor_a1_used,
            'sensor_a2_used': sensor_a2_used,
            'sensor_a3_used': sensor_a3_used,
            'sensor_a4_used': sensor_a4_used,
            'sensor_a0_purpose': sensor_a0_purpose,
            'sensor_a1_purpose': sensor_a1_purpose,
            'sensor_a2_purpose': sensor_a2_purpose,
            'sensor_a3_purpose': sensor_a3_purpose,
            'sensor_a4_purpose': sensor_a4_purpose
        }

        # Submit button
        create_gesture_submitted = st.form_submit_button("Create Gesture")
        
        if create_gesture_submitted:
            create_gesture(selected_user_id, gesture_description, sensors)
            st.success(f"Gesture created successfully for {selected_user}!")

# List all user gestures
    st.markdown("---")
    st.subheader(f"Gestures for {selected_user}")
    gestures = fetch_gestures(selected_user_id)
    gestures_df = pd.DataFrame(gestures, columns=["GestureID", "UserID", "Gesture Description", 
                                                  "Sensor A0 Used", "Sensor A1 Used", 
                                                  "Sensor A2 Used", "Sensor A3 Used", 
                                                  "Sensor A4 Used", "Sensor A0 Purpose", 
                                                  "Sensor A1 Purpose", "Sensor A2 Purpose", 
                                                  "Sensor A3 Purpose", "Sensor A4 Purpose"])
    
    # Remove UserID from the display
    gestures_df = gestures_df.drop(columns=["UserID"])

    # Add delete buttons next to each gesture
    
    for i, row in gestures_df.iterrows():
        col1, col2 = st.columns([4, 1])
        col1.write(row)
        delete_button = col2.button("Delete", key=row["GestureID"])
        if delete_button:
            delete_gesture(row["GestureID"])
            st.success(f"Gesture {row['Gesture Description']} deleted successfully!")
            st.rerun()