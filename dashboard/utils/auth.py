
# dashboard/utils/auth.py
import streamlit as st
import sqlite3

def check_credentials(username, password):
    conn = sqlite3.connect('database/windrush.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username=? AND password=?', 
             (username, password))
    return c.fetchone()

def role_based_access(required_role):
    if 'role' not in st.session_state or st.session_state.role != required_role:
        st.error("Unauthorized Access")
        st.stop()