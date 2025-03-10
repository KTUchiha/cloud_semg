import streamlit as st
import psycopg2
import pandas as pd

# Set up a connection to the PostgreSQL database
def init_connection():
    return psycopg2.connect(
        host="localhost",       # Adjust as necessary
        database="sensordb",
        user="XXXXXXX",
        password="XXXXXXXX"
    )

# Initialize connection
conn = init_connection()
cursor = conn.cursor()

# Function to create a new user
def create_user(first_name, last_name, email, description):
    query = """INSERT INTO users (first_name, last_name, email, personal_description) 
               VALUES (%s, %s, %s, %s);"""
    cursor.execute(query, (first_name, last_name, email, description))
    conn.commit()

# Function to fetch all users
def fetch_users():
    cursor.execute("SELECT * FROM users;")
    return cursor.fetchall()

# Function to update a user
def update_user(userid, first_name, last_name, email, description):
    query = """UPDATE users SET first_name = %s, last_name = %s, email = %s, personal_description = %s 
               WHERE userid = %s;"""
    cursor.execute(query, (first_name, last_name, email, description, userid))
    conn.commit()

# Function to delete a user
def delete_user(userid):
    cursor.execute("DELETE FROM users WHERE userid = %s;", (userid,))
    conn.commit()

# Streamlit Interface
st.title("User Management")

# Create User Form
with st.form("create_user"):
    st.subheader("Create a New User")
    first_name = st.text_input("First Name")
    last_name = st.text_input("Last Name")
    email = st.text_input("Email")
    description = st.text_area("Personal Description")
    submitted = st.form_submit_button("Create User")
    
    if submitted:
        create_user(first_name, last_name, email, description)
        st.success(f"User {first_name} {last_name} created successfully!")

# List all users
st.subheader("All Users")
users = fetch_users()
users_df = pd.DataFrame(users, columns=["UserID", "First Name", "Last Name", "Email", "Description"])
st.dataframe(users_df)

# Update/Delete User
st.subheader("Update or Delete a User")
user_id_to_modify = st.selectbox("Select a User to Modify", users_df['UserID'])

if user_id_to_modify:
    # Select user information
    selected_user = users_df[users_df['UserID'] == user_id_to_modify].iloc[0]
    
    # Update form
    with st.form("update_user"):
        first_name = st.text_input("First Name", selected_user['First Name'])
        last_name = st.text_input("Last Name", selected_user['Last Name'])
        email = st.text_input("Email", selected_user['Email'])
        description = st.text_area("Personal Description", selected_user['Description'])
        update_submitted = st.form_submit_button("Update User")
        
        if update_submitted:
            update_user(user_id_to_modify, first_name, last_name, email, description)
            st.success(f"User {first_name} {last_name} updated successfully!")
    
    # Delete user button
    if st.button("Delete User"):
        delete_user(user_id_to_modify)
        st.success(f"User {user_id_to_modify} deleted successfully!")
        
