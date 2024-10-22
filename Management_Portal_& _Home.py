import streamlit as st
from io import BytesIO
from embedchain import App
from utils import *
from openai import OpenAI

client = OpenAI()
from chardet.universaldetector import UniversalDetector
from streamlit_authenticator import Authenticate
import re

st.set_page_config(page_title="YourHome.ai", page_icon=":house", layout="centered", initial_sidebar_state="auto", menu_items=None)

def detect_file_encoding(file_path):
    detector = UniversalDetector()
    with open(file_path, 'rb') as f:
        for line in f:
            detector.feed(line)
            if detector.done:
                break
        detector.close()
    return detector.result['encoding']

def main(authenticator):

    st.sidebar.title("Welcome to YourHome.ai")
    page = st.sidebar.radio("Navigation", ["Login", "Register"], key='navigation_radio')  # Add a unique key

    if page == "Login":
        st.title("Login to Your Account")
        
        # Call the login function from the Authenticate class
        name, auth_status, email = authenticator.login('Login', 'main')

        if auth_status:
            st.success(f"Welcome {name}")
            st.title('Management Portal')

            # Realtor Listing Creation Section
            st.subheader("Create Upload Portal")
            address = st.text_input("Enter the address for the listing:", key='create_listing_address')  # Add key
            if st.button("Create Listing", key='create_listing_button'):  # Add key
                save_listing(address)
                st.success(f"Listing for {address} created successfully!")

            # Analyze Candidates for an Address Section
            st.subheader("Analyze Tenant Documents")
            available_listings = fetch_created_listings()
            if not available_listings:
                st.warning("No listings available at the moment.")
                return

            selected_address = st.selectbox("Select a listing:", available_listings, key='select_listing')  # Add key
            tenants = get_tenants_for_address(selected_address)
            selected_tenant = st.selectbox("Select a tenant:", [t.replace('_', ' ') for t in tenants], key='select_tenant')  # Add key
            selected_tenant = selected_tenant.replace(' ', '_') if selected_tenant != None else None

            # List documents for the selected tenants
            file_names, files = list_files_for_tenant(selected_address, selected_tenant)
            meta_datas = []
            doc_types = []
            
            # Extract document categories
            document_categories = set()
            for file in files:
                metadata = get_metadata_for_file(BUCKET_NAME, file['Key'])
                meta_datas.append(metadata)
                document_type = metadata.get('document_type', '').lower()
                doc_types.append(document_type)
                document_categories.add(document_type)

            document_categories = list(document_categories)
            selected_category = st.selectbox("Select a document to view:", document_categories, key='select_document')  # Add key

            # Fetch the corresponding document for the selected category
            selected_file = next((file for i, file in enumerate(file_names) if selected_category in doc_types[i]), None)
            if st.button("Analyze Document", key='analyze_document_button'):  # Add key
                file_key = selected_file
                file_data = download_file_from_s3(BUCKET_NAME, file_key)
                file_type = determine_data_type(selected_file)

                if file_type == "pdf_file":
                    display_pdf(file_data)
                elif file_type == "image":
                    st.image(file_data)
                elif file_type == "text":
                    content = file_data.decode("utf-8")
                    if "youtube.com" in content or "youtu.be" in content:
                        st.video(content)
                    else:
                        st.text(content)
                else:
                    st.warning("Unsupported file type for direct viewing. Please download the file instead.")
                    presigned_url = generate_presigned_url(BUCKET_NAME, file_key)
                    st.write(f"[Click here to view/download {selected_file}]({presigned_url})")

                st.markdown("### Evaluation")
                files = get_files_for_tenant(selected_address, selected_tenant, only_text=True)
                file = [file for file in files if file_type.lower() in file['Key'].lower()]
                for file in files:
                    meta_data = get_metadata_for_file(BUCKET_NAME, file['Key'])
                    doc_type = meta_data.get('document_type', '').lower()
                    if selected_category.lower() in doc_type:
                        break
                doc_type = doc_type.replace('_', ' ')
                
                presigned_url = generate_presigned_url(BUCKET_NAME, file['Key'])
                st.markdown(presigned_url)
                local_file_path = download_from_presigned_url(presigned_url)
                file_encoding = detect_file_encoding(local_file_path)
                with open(local_file_path, 'r', encoding=file_encoding) as f:
                    file_content = f.read()

                name = selected_tenant.replace('_', ' ')
                address = selected_address
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo-0125",
                    messages=[
                        {'role': 'system', 'content': f'You are a critical property manager and are currently evaluating a prospective tenant named {name} for a rental property located at {address}. Your goal is to evaluate the tenant and determine whether they are a good fit for the property. Pay close attention to key metrics like credit score, income level and job stability. Be highly suspect of any red flags.'},
                        {"role": "user", "content": f"Based on the following document from {name} with document type {doc_type}, provide concise meaningful commentary on whether {name} is a good fit for the property.\n ```{file_content}```"}
                    ],
                    temperature=0.0
                )
                response_text = response.choices[0].message.content
                response_text = response_text.replace('*', '\*').replace('_', '\_').replace('\xa0', ' ').replace('$', '\$')
                st.markdown(response_text)

        elif auth_status == False:
            st.error("Login failed. Please check your email and password.")
        elif auth_status == None:
            st.warning("Please enter your credentials.")

    elif page == "Register":
        st.title("Create a New Account")
        # Call the register function from the Authenticate class
        if authenticator.register_user('Register', 'main', preauthorization=False):
            st.success("Registration successful! You can now log in.")
        else:
            st.warning("Please fill out the form to register.")

if __name__ == "__main__":
    st.session_state['authenticator'] = Authenticate("nachozobian", "Hola", 30)
    if 'authentication_status' not in st.session_state:
        st.session_state['authentication_status'] = None
    if 'verified' not in st.session_state:
        st.session_state['verified'] = None
    if st.session_state['verified'] and st.session_state["authentication_status"]:
        if 'subscribed' not in st.session_state:
            st.session_state['subscribed'] = is_email_subscribed(st.session_state['email'])
            
main(authenticator=st.session_state['authenticator'])