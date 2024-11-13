import streamlit as st
import boto3
from io import BytesIO
from embedchain import App
from utils import *
from streamlit_authenticator import Authenticate

def main():
    st.title('Tenant ChatBot')
    
    # Redirect to Stripe checkout if URL is present in session state
    if 'checkout_url' in st.session_state:
        checkout_url = st.session_state.pop('checkout_url')  # Get and remove the URL from session state
        st.write(f"<meta http-equiv='refresh' content='0; url={checkout_url}'>", unsafe_allow_html=True)
        return
    
    # Analyze Candidates for an Address Section
    available_listings = fetch_created_listings()
    if not available_listings:
        st.warning("No listings available at the moment.")
        return

    selected_address = st.selectbox("Select a listing:", available_listings)
    tenants = get_tenants_for_address(selected_address)
    if tenants:
        tenant_options = [t.replace('_', ' ') for t in tenants]
        selected_tenant = st.selectbox("Select a tenant:", tenant_options)
    else:
        st.warning("No tenants available for this listing.")
        return

    # Initialize embedchain app
    if st.button("Chat with tenant?"):
        if not is_email_subscribed(st.session_state['email']):
            st.warning("You need to subscribe to access this feature.")
            st.session_state['subscribe_now'] = True  # Set subscription state flag
        else:
            st.session_state['bot'] = create_bot(selected_address, selected_tenant)

        
    # Check if the user needs to subscribe
    if st.session_state.get('subscribe_now'):
        if st.button("Subscribe Now"):
            # Redirect to Stripe payment portal
            subscribe_user()  # This function should handle the Stripe payment process
            return

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
        st.session_state['authenticator'] = Authenticate("nachozobian", "350key", 30)
    if 'authentication_status' not in st.session_state:
        st.session_state['authentication_status'] = None
    if 'name' not in st.session_state:
        st.session_state['name'] = None
    if 'username' not in st.session_state:
        st.session_state['username'] = None
    if 'email' not in st.session_state:
        st.session_state['email'] = None

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
            st.session_state['email'] = username  # Assuming username is the email
            st.experimental_rerun()
        elif authentication_status == False:
            st.error('Username/password is incorrect')
        elif authentication_status == None:
            st.warning('Please enter your username and password')
