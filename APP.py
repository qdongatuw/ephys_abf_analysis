import streamlit as st


uploaded_file = st.file_uploader(label='Upload ABF files', accept_multiple_files=True,  type=['abf'])
st.write(uploaded_file)