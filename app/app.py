import sqlite3 as sql
import time
from contextlib import closing

import bcrypt
import streamlit as st

d_b = "users.db"


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
    st.write("PASSWORD UPDATED")
    time.sleep(1)
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
                        st.switch_page("/home/res/app/pages/page2.py")
                    else:
                        st.error("Wrong password")

                else:
                    st.write("Record Not found!")
            else:
                PID = add_user(name, email, hash_pass(password), d_b)
                st.write("NOTE YOUR PID: ")
                st.write(PID)
                st.rerun()

    with tab2:
        email = st.text_input("Enter your email ", key="fp_email")
        if email:
            if search_user(email, d_b):
                npass = st.text_input(
                    "Enter new password ", type="password", key="fp_npass"
                )
                if st.button("update", key="fp_update"):
                    if npass:
                        update_pass(email, npass, d_b)
                        st.switch_page("app")
                    else:
                        st.error("Enter new password")
            else:
                st.error("User not found")
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
