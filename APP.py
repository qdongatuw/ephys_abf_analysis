import streamlit as st
import pyabf

# Create a file upload widget
uploaded_file = st.file_uploader("Upload a file", type=['abf'], accept_multiple_files=False)

# Check if a file is uploaded
if uploaded_file is not None:
    # Get the file name
    file_name = uploaded_file.name
    f = pyabf.ABF(file_name)
    st.write(f)
    