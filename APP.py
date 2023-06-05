import streamlit as st

# Create a file upload widget
uploaded_file = st.file_uploader("Upload a file", type=['abf'])

# Check if a file is uploaded
if uploaded_file is not None:
    # Get the file name
    file_name = uploaded_file.name
    
    # Display the file name as a clickable link
    file_link = f"[{file_name}]({uploaded_file.name})"
    st.markdown(file_link, unsafe_allow_html=True)
    
    # Trigger an event when the file name is clicked
    if st.button("Click here"):
        # Perform your desired action
        st.write("File name clicked!")