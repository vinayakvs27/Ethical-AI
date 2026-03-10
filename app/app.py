import os
import time
import random
import base64
import sqlite3 as sql
from contextlib import closing
from email.message import EmailMessage

import google.auth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import bcrypt
import streamlit as st
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if st.session_state.logged_in:
    st.switch_page("pages/task.py")
    
d_b = "users.db"
store={}

def init_db(path=d_b):
    with sql.connect(path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("""
            create table if not exists user_pid
            (
                pid integer primary key autoincrement,
                email text unique not null
            )
        """)
        conn.execute("""
            create table if not exists user_info
            (
                name text not null,
                email text unique not null,
                password_hash text not null,
                pid integer not null,
                foreign key (pid) references user_pid(pid)
            )
        """)
        conn.commit()


def add_pid(email, path=d_b):
    with sql.connect(path) as conn:
        cur = conn.cursor()
        _ = cur.execute(
            """
            insert into user_pid(email)
            values(?)
            """,
            (email,),
        )
        _ = cur.execute(
            """
            select pid from user_pid where email=?
            """,
            (email,),
        )
        conn.commit()
        return cur.fetchone()[0]


def get_pid(email, path=d_b):
    with sql.connect(path) as conn:
        cur = conn.cursor()
        if search_user(email, path):
            cur.execute(
                """
                select pid from user_pid where email=?
                """,
                (email,),
            )
        return cur.fetchone()[0]


def add_user(name, email, password_hash, path=d_b):
    val = add_pid(email, d_b)
    with sql.connect(path) as conn:
        cur = conn.cursor()
        _ = cur.execute(
            """insert into user_info (name,email,password_hash,pid)
            values(?,?,?,?)
            """,
            (name, email, password_hash, val),
        )
        conn.commit()
    return get_pid(email, d_b)


def update_pass(email, npass, path=d_b):
    with sql.connect(path) as conn:
        cur = conn.cursor()
        _ = cur.execute(
            """
            UPDATE user_info SET password_hash=? where email=?
            """,
            (hash_pass(npass), email),
        )
        conn.commit()
    st.success("PASSWORD UPDATED SUCCESSFULLY!")
    time.sleep(1.5)
    
        # err
    if 'otp_sent' in st.session_state: del st.session_state['otp_sent']
    if 'otp_valid' in st.session_state: del st.session_state['otp_valid']
    
    st.rerun()


def search_user(email, path=d_b):
    with sql.connect(path) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            select exists(
            select 1
            from user_info
            where email =?
            )
            """,
            (email,),
        )
        return cur.fetchone()[0]


def delete_user(email, path=d_b):
    with sql.connect(path) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            delete from user_info where email=?
            """,
            (email,),
        )
        cur.execute(
            """
            delete from user_pid where email=?
            """,
            (email,),
        )
        conn.commit()
        st.write("Account successfully deleted!! ")
        time.sleep(2)
        st.rerun()


def hash_pass(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_pass(password: str, hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), hash.encode())


def get_hash(email, path=d_b):
    with sql.connect(path) as conn:
        cur = conn.cursor()
        _ = cur.execute(
            """
            select password_hash
            from user_info
            where email=?
            """,
            (email,),
        )
        return cur.fetchone()[0]


SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def get_credentials():
    """Handles the OAuth 2.0 flow and token management."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds
def set_key(key,value,ttl):
    expiry=time.monotonic()+ttl
    store[key]=(value,expiry) 
def get_key(key):
    item=store.get(key)
    if not item:
        return None
    value,expiry=item
    if time.monotonic()>expiry:
        del store[key]
        return None
    return value

def gen_otp(email):
    """Generates and sends an OTP via Gmail API."""
    creds = get_credentials()
    
    try:
        service = build("gmail", 'v1', credentials=creds)
        message = EmailMessage()
        
        otp_code = random.randint(100000, 999999)
        otp_text = f"{otp_code} is your OTP for ETHICAL-AI, password RESET"
        
        message.set_content(otp_text)
        message["To"] = email
        message["From"] = "res1076@gmail.com" # Ensure this matches your auth email
        message["Subject"] = "OTP for reset"
        
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {"raw": encoded_message}
        
        send_message = (
            service.users()
            .messages()
            .send(userId="me", body=create_message)
            .execute()
        )
        print(f'Message Id: {send_message["id"]}')
        
        # FIX: Store OTP and Expiry in Streamlit's Session State
        st.session_state.generated_otp = otp_code
        st.session_state.otp_expiry = time.time() + 60 # 60 seconds TTL
        
        return send_message
        
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None
    
_ = st.title("Ethical AI")
tab1, tab2, tab3 = st.tabs(["Login", "Forgot Password", "Delete Account"])
init_db(d_b)
with tab1:
    with st.form(key="user_login_details", clear_on_submit=True):
        name = st.text_input("Enter your name ")
        email = st.text_input("Enter your email ")
        password = st.text_input("Password ", type="password")
        submit = st.form_submit_button("LOGIN")
        if submit:
            if search_user(email, d_b):
                hash = get_hash(email, d_b)
                if hash:
                    if check_pass(password, get_hash(email, d_b)):
                        st.session_state.logged_in = True
                        st.success("Login successful!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Wrong password")

                else:
                    st.write("Record Not found!")
            else:
                PID = add_user(name, email, hash_pass(password), d_b)
                st.write("NOTE YOUR PID: ")
                st.write(PID)
                time.sleep(10)
with tab2:
        st.subheader("Reset Your Password")
        email = st.text_input("Enter your email ", key="fp_email")

        # Initialize session state variables for this tab
        if 'otp_sent' not in st.session_state:
            st.session_state.otp_sent = False
        if 'otp_valid' not in st.session_state:
            st.session_state.otp_valid = False

        if email:
            if search_user(email, d_b):
                
                # STEP 1: Send the OTP
                if not st.session_state.otp_sent:
                    if st.button("Send OTP", key="send_otp_btn"):
                        gen_otp(email)
                        st.session_state.otp_sent = True
                        st.rerun() # Force a rerun to render the next step
                
                # STEP 2: Validate the OTP
                if st.session_state.otp_sent and not st.session_state.otp_valid:
                    st.info("OTP sent to your email. It expires in 60 seconds.")
                    otp_input = st.text_input("ENTER OTP ", key="fp_otp")
                    
                    if st.button("Validate OTP", key="val_otp_btn"):
                        # FIX: Clean the input to remove accidental spaces
                        clean_input = otp_input.strip() 
                        
                        # FIX: Retrieve from session state instead of the global dictionary
                        stored_otp = st.session_state.get("generated_otp")
                        expiry_time = st.session_state.get("otp_expiry", 0)
                        
                        if time.time() > expiry_time:
                            st.error("OTP has expired. Please send a new one.")
                            st.session_state.otp_sent = False # Reset flow so they can send again
                        elif stored_otp and clean_input.isdigit() and int(clean_input) == stored_otp:
                            st.session_state.otp_valid = True
                            st.success("OTP Verified!")
                            time.sleep(1)
                            st.rerun() # Force a rerun to show the password reset fields
                        else:
                            st.error("Wrong OTP. Please try again.")

                # STEP 3: Update the Password
                if st.session_state.otp_valid:
                    st.success("You can now securely reset your password.")
                    npass = st.text_input("Enter new password ", type="password", key="fp_npass")
                    
                    if st.button("Update Password", key="fp_update"):
                        if npass:
                            update_pass(email, npass, d_b)
                        else:
                            st.error("Please enter a valid new password.")
            else:
                st.error("User not found in our database.")
with tab3:
        email = st.text_input("Enter email to delete")
        if email:
            if search_user(email, d_b):
                password = st.text_input("Enter password")
                if st.button("Delete"):
                    if check_pass(password, get_hash(email, d_b)):
                        delete_user(email, d_b)
                    else:
                        st.error("Wrong password or user not found")
            else:
                st.error(" user not found ")

if st.session_state.logged_in:
    st.switch_page("pages/task.py")
