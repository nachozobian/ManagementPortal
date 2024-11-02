import streamlit as st
import boto3
from io import BytesIO
from embedchain import App
from utils import *
from streamlit_authenticator import Authenticate

def main():
    st.title('Tenant ChatBot')

    # Analyze Candidates for an Address Section
    available_listings = fetch_created_listings()
    if not available_listings:
        st.warning("No listings available at the moment.")
        return

    selected_address = st.selectbox("Select a listing:", available_listings)
    tenants = get_tenants_for_address(selected_address)
    if tenants:
        selected_tenant = st.selectbox("Select a tenant:", tenants)
    else:
        st.warning("No tenants available for this listing.")
        return

    # Initialize embedchain app
    if st.button("Chat with tenant?"):
        st.session_state['bot'] = create_bot(selected_address, selected_tenant)

    if "bot" in st.session_state:
        # Start Chatbot and Reset Conversation buttons
        reset_chat = st.button("Reset Conversation")
        
        if reset_chat:
            st.session_state.messages = []

        # Chatbot functionality with streaming
        if "messages" not in st.session_state:
            st.session_state.messages = []

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input("Ask a question about the documents:"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""
                responses = st.session_state['bot'].chat(prompt)
                for chunk in responses:
                    full_response += chunk
                    message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})

if __name__ == "__main__":
    # Initialize authenticator and session state variables
    if 'authenticator' not in st.session_state:
        st.session_state['authenticator'] = Authenticate("smartbidscookie3124", "smartbidskey3214", 30)
    if 'authentication_status' not in st.session_state:
        st.session_state['authentication_status'] = None
    if 'name' not in st.session_state:
        st.session_state['name'] = None
    if 'username' not in st.session_state:
        st.session_state['username'] = None

    # Check authentication status
    if st.session_state['authentication_status']:
        st.sidebar.title(f"Welcome {st.session_state.get('name')}")
        st.session_state['authenticator'].logout('Logout', 'sidebar')
        main()
    else:
        name, authentication_status, username = st.session_state['authenticator'].login('Login', 'main')
        if authentication_status:
            st.session_state['authentication_status'] = True
            st.session_state['name'] = name
            st.session_state['username'] = username
            st.experimental_rerun()
        elif authentication_status == False:
            st.error('Username/password is incorrect')
        elif authentication_status == None:
            st.warning('Please enter your username and password')
