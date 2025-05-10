import streamlit as st
import psycopg2
import pandas as pd
import numpy as np
import json
from datetime import datetime

# Set up connection to PostgreSQL database
def init_connection():
    return psycopg2.connect(
        host=os.environ['POSTGRES_HOST'],
        database=os.environ['POSTGRES_DB'],
        user=os.environ['POSTGRES_USER'],
        password=os.environ['POSTGRES_PASSWORD']
    )
# Initialize connection
conn = init_connection()
cursor = conn.cursor()

# Function to fetch all users
def fetch_users():
    cursor.execute("SELECT * FROM users;")
    return cursor.fetchall()

# Function to fetch user gestures for a specific user
def fetch_gestures(userid):
    cursor.execute("SELECT * FROM user_gestures WHERE userid = %s;", (userid,))
    return cursor.fetchall()

# Function to fetch existing haptic mappings for a gesture
def fetch_haptic_mappings(gestureid):
    cursor.execute("""
        SELECT * FROM gesture_haptic_mapping 
        WHERE gestureid = %s 
        ORDER BY sequence_order ASC;
    """, (gestureid,))
    return cursor.fetchall()

# Function to save a haptic mapping
def save_haptic_mapping(gestureid, userid, sequence_order, motor_states):
    # Check if mapping already exists for this sequence
    cursor.execute("""
        SELECT mapping_id FROM gesture_haptic_mapping 
        WHERE gestureid = %s AND sequence_order = %s;
    """, (gestureid, sequence_order))
    
    existing_mapping = cursor.fetchone()
    
    if existing_mapping:
        # Update existing mapping
        update_query = """
            UPDATE gesture_haptic_mapping SET 
                thumb_tip = %s, thumb_base = %s, 
                index_tip = %s, index_base = %s, 
                middle_tip = %s, middle_base = %s, 
                ring_tip = %s, ring_base = %s, 
                pinky_tip = %s, pinky_base = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE mapping_id = %s;
        """
        cursor.execute(update_query, (
            motor_states['thumb_tip'], motor_states['thumb_base'],
            motor_states['index_tip'], motor_states['index_base'],
            motor_states['middle_tip'], motor_states['middle_base'],
            motor_states['ring_tip'], motor_states['ring_base'],
            motor_states['pinky_tip'], motor_states['pinky_base'],
            existing_mapping[0]
        ))
    else:
        # Create new mapping
        insert_query = """
            INSERT INTO gesture_haptic_mapping (
                gestureid, userid, sequence_order, 
                thumb_tip, thumb_base, 
                index_tip, index_base, 
                middle_tip, middle_base, 
                ring_tip, ring_base, 
                pinky_tip, pinky_base
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        cursor.execute(insert_query, (
            gestureid, userid, sequence_order,
            motor_states['thumb_tip'], motor_states['thumb_base'],
            motor_states['index_tip'], motor_states['index_base'],
            motor_states['middle_tip'], motor_states['middle_base'],
            motor_states['ring_tip'], motor_states['ring_base'],
            motor_states['pinky_tip'], motor_states['pinky_base']
        ))
    
    conn.commit()

# Function to delete a haptic mapping
def delete_haptic_mapping(gestureid):
    cursor.execute("DELETE FROM gesture_haptic_mapping WHERE gestureid = %s;", (gestureid,))
    conn.commit()

# Function to count active motors
def count_active_motors(motor_states):
    return sum(1 for state in motor_states.values() if state)

# Main Streamlit app
st.title("Gesture to Haptic Feedback Mapping")

# Fetch users and create a dropdown
users = fetch_users()
users_df = pd.DataFrame(users, columns=["UserID", "First Name", "Last Name", "Email", "Description"])
users_df["Full Name"] = users_df["First Name"] + " " + users_df["Last Name"]

# Select user
selected_user = st.selectbox("Select User", users_df["Full Name"])
selected_user_row = users_df[users_df["Full Name"] == selected_user]
selected_user_id = int(selected_user_row["UserID"].values[0])

# Fetch gestures for the selected user
if selected_user_id:
    gestures = fetch_gestures(selected_user_id)
    if gestures:
        gestures_df = pd.DataFrame(gestures, columns=["GestureID", "UserID", "Gesture Description", 
                                                   "Sensor A0 Used", "Sensor A1 Used", 
                                                   "Sensor A2 Used", "Sensor A3 Used", 
                                                   "Sensor A4 Used", "Sensor A0 Purpose", 
                                                   "Sensor A1 Purpose", "Sensor A2 Purpose", 
                                                   "Sensor A3 Purpose", "Sensor A4 Purpose"])
        
        # Select gesture
        gesture_options = [(g[0], g[2]) for g in gestures]  # (gesture_id, description)
        selected_gesture = st.selectbox("Select Gesture", 
                                      options=[g[0] for g in gesture_options],
                                      format_func=lambda x: next((g[1] for g in gesture_options if g[0] == x), ""))
        
        if selected_gesture:
            st.write(f"### Creating Haptic Mapping for: {next((g[1] for g in gesture_options if g[0] == selected_gesture), '')}")
            
            # Get existing mappings
            existing_mappings = fetch_haptic_mappings(selected_gesture)
            
            # Create tabs for sequence steps
            tabs = st.tabs(["Sequence 1", "Sequence 2", "Sequence 3", "Sequence 4", "Sequence 5"])
            
            # Define the finger layout for visualization
            finger_names = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
            
            # Process each tab/sequence
            for i, tab in enumerate(tabs):
                with tab:
                    st.write(f"### Sequence {i+1} - {300}ms activation, {150}ms rest")
                    
                    # Initialize motor states for this sequence
                    motor_states = {
                        'thumb_tip': False, 'thumb_base': False,
                        'index_tip': False, 'index_base': False,
                        'middle_tip': False, 'middle_base': False,
                        'ring_tip': False, 'ring_base': False,
                        'pinky_tip': False, 'pinky_base': False
                    }
                    
                    # Load existing mapping if available
                    existing_mapping = next((m for m in existing_mappings if m[2] == i+1), None)
                    if existing_mapping:
                        motor_states = {
                            'thumb_tip': existing_mapping[4], 'thumb_base': existing_mapping[5],
                            'index_tip': existing_mapping[6], 'index_base': existing_mapping[7],
                            'middle_tip': existing_mapping[8], 'middle_base': existing_mapping[9],
                            'ring_tip': existing_mapping[10], 'ring_base': existing_mapping[11],
                            'pinky_tip': existing_mapping[12], 'pinky_base': existing_mapping[13]
                        }
                    
                    # Create visual hand layout
                    st.write("#### Select Motors to Activate (max 4)")
                    
                    # Count active motors to enforce limit
                    active_count = count_active_motors(motor_states)
                    
                    # Create the finger layout using columns
                    cols = st.columns(5)
                    
                    for j, (finger, col) in enumerate(zip(finger_names, cols)):
                        col.write(f"**{finger}**")
                        
                        # Determine the motor keys for this finger
                        tip_key = f"{finger.lower()}_tip"
                        base_key = f"{finger.lower()}_base"
                        
                        # Create checkboxes for tip and base motors
                        if tip_key in motor_states:
                            motor_states[tip_key] = col.checkbox(
                                f"Tip", 
                                value=motor_states[tip_key],
                                key=f"seq_{i+1}_{tip_key}",
                                disabled=(active_count >= 4 and not motor_states[tip_key])
                            )
                        
                        if base_key in motor_states:
                            motor_states[base_key] = col.checkbox(
                                f"Base", 
                                value=motor_states[base_key],
                                key=f"seq_{i+1}_{base_key}",
                                disabled=(active_count >= 4 and not motor_states[base_key])
                            )
                    
                    # Update active count for warning message
                    active_count = count_active_motors(motor_states)
                    
                    # Show warning if too many motors are active
                    if active_count > 4:
                        st.warning(f"❗ You have selected {active_count} motors. Maximum allowed is 4.")
                    elif active_count == 0:
                        st.info("ℹ️ No motors selected for this sequence. It will be skipped.")
                    else:
                        st.success(f"✅ {active_count} motors selected for this sequence.")
                    
                    # Save button for this sequence
                    if st.button(f"Save Sequence {i+1}", key=f"save_seq_{i+1}"):
                        save_haptic_mapping(selected_gesture, selected_user_id, i+1, motor_states)
                        st.success(f"✅ Sequence {i+1} saved successfully!")
            
            # Add a visual summary of the entire sequence
            st.write("---")
            st.write("### Haptic Sequence Summary")
            
            # Refresh existing mappings
            existing_mappings = fetch_haptic_mappings(selected_gesture)
            
            if existing_mappings:
                # Create a table visualization
                summary_data = []
                for mapping in existing_mappings:
                    sequence_order = mapping[2]
                    active_motors = []
                    
                    for i, finger in enumerate(finger_names):
                        tip_index = 4 + i*2
                        base_index = 5 + i*2
                        
                        if mapping[tip_index]:
                            active_motors.append(f"{finger} Tip")
                        if mapping[base_index]:
                            active_motors.append(f"{finger} Base")
                    
                    summary_data.append({
                        "Sequence": sequence_order,
                        "Active Motors": ", ".join(active_motors) if active_motors else "None",
                        "Duration": "300ms active, 150ms rest"
                    })
                
                summary_df = pd.DataFrame(summary_data)
                st.table(summary_df)
                
                # Total duration calculation
                total_sequences = len(existing_mappings)
                total_duration_ms = total_sequences * 450  # 300ms active + 150ms rest
                st.write(f"**Total Haptic Pattern Duration:** {total_duration_ms} ms")
                
                # Delete all mappings button
                if st.button("Delete All Mappings for this Gesture", key="delete_all"):
                    delete_haptic_mapping(selected_gesture)
                    st.warning("⚠️ All haptic mappings for this gesture have been deleted.")
                    st.rerun()
            else:
                st.info("No haptic mappings defined yet for this gesture.")
    else:
        st.warning("No gestures found for this user. Please create gestures first.")