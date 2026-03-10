import streamlit as st
from pathlib import Path
st.set_page_config(layout="wide")

st.markdown("<h1 style='text-align: center;'>Select Task</h1>", unsafe_allow_html=True)
st.markdown("<h4 style='text-align: center;'>Choose the task you want to perform</h4>", unsafe_allow_html=True)

st.write("")
left, center1, center2, right = st.columns([1,2,2,1])

BASE_DIR = Path(__file__).resolve().parent.parent
heart_img = BASE_DIR / "images" / "heart_disease.jpg"
xray_img = BASE_DIR / "images" / "xray_diagram.jpg"

with center1:
    st.image(str(heart_img), use_column_width=True)
    if st.button("Heart Disease", use_container_width=True):
        st.switch_page("pages/page1.py")

with center2:
    st.image(str(xray_img), use_column_width=True)
    if st.button("Xray", use_container_width=True):
        st.switch_page("pages/page2.py")
