import os
import streamlit as st
import pyabf

# Create a file upload widget
uploaded_file = st.file_uploader("Upload a file", type=['abf'], accept_multiple_files=False)

# Check if a file is uploaded
if uploaded_file is not None:
    # Specify the directory to save the uploaded file
    save_directory = "./uploads"

    # Create the directory if it doesn't exist
    os.makedirs(save_directory, exist_ok=True)

    # Save the uploaded file to the specified directory
    file_path = os.path.join(save_directory, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getvalue())

    # Load the ABF file using pyabf
    abf = pyabf.ABF(file_path)

    st.write(abf)
    