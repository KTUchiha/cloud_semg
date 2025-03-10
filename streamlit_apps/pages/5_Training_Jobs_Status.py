import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px

# Initialize database connection
def init_connection():
    return psycopg2.connect(
        host="localhost",
        database="sensordb",
        user="kaavya",
        password="sEMG1234"  # Your password here
    )

# Function to fetch users
def fetch_users(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users;")
    return cursor.fetchall()

# Function to fetch training job status for a user, ordered by most recent first
def fetch_training_jobs_for_user(conn, user_id):
    cursor = conn.cursor()
    query = """
    SELECT job_id, job_status, num_samples, actual_start_time, actual_end_time, error_message, log_messages
    FROM training_job_schedule 
    WHERE userid = %s
    ORDER BY job_id DESC;  -- Most recent job first
    """
    cursor.execute(query, (user_id,))
    rows = cursor.fetchall()
    return rows

# Streamlit UI
st.title("Training Job Status")

# Initialize connection
conn = init_connection()



# Fetch all users
users = fetch_users(conn)

# Create a dropdown to select a user
user_options = [(f"{user[1]} {user[2]}", user[0]) for user in users]  # (user_full_name, user_id)
user_selected = st.selectbox("Select User", user_options, format_func=lambda x: x[0])

if user_selected:
    user_id = user_selected[1]

    # Fetch training jobs for the selected user
    training_jobs = fetch_training_jobs_for_user(conn, user_id)
    
    if training_jobs:
        job_columns = ["Job ID", "Status", "Number of Samples", "Start Time", "End Time", "Error Message", "Log Messages"]
        df = pd.DataFrame(training_jobs, columns=job_columns)
        
        st.subheader("Training Jobs for User")
        st.dataframe(df)  # Display the DataFrame with the most recent job first
        
        # Show detailed view of a selected job
        st.subheader("Select a Job to View Details")
        job_selected = st.selectbox("Select Job ID", df['Job ID'].unique())
        
        if job_selected:
            # Refresh button
            if st.button("Refresh Job Status"):
                st.rerun()
            selected_job = df[df['Job ID'] == job_selected].iloc[0]
            st.write("### Job Details:")
            cols=st.columns(5)
            cols[0].write(f"**Job ID:** {selected_job['Job ID']}")
            cols[1].write(f"**Status:** {selected_job['Status']}")
            cols[2].write(f"**Number of Samples:** {selected_job['Number of Samples']}")
            cols[3].write(f"**Start Time:** {selected_job['Start Time']}")
            cols[4].write(f"**End Time:** {selected_job['End Time']}")
            st.write(f"**Error Message:** {selected_job['Error Message']}")
            st.write("### Log Messages:")
            st.text_area("", selected_job['Log Messages'], height=200)
    else:
        st.write("No training jobs found for this user.")

# Close the connection
conn.close()
