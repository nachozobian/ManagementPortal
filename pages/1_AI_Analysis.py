import streamlit as st
from io import BytesIO
from embedchain import App
from utils import *
import openai

from chardet.universaldetector import UniversalDetector
from streamlit_authenticator import Authenticate
import re

def detect_file_encoding(file_path):
    # Function to detect file encoding
    detector = UniversalDetector()
    with open(file_path, 'rb') as f:
        for line in f:
            detector.feed(line)
            if detector.done:
                break
        detector.close()
    return detector.result['encoding']

def main():
    st.title('Analyze Tenant Documents')

    # Analyze Candidates for an Address Section
    st.subheader("Analyze Tenant Documents")
    available_listings = fetch_created_listings()
    if not available_listings:
        st.warning("No listings available at the moment.")
        return

    selected_address = st.selectbox("Select a listing:", available_listings)

    tenants = get_tenants_for_address(selected_address)
    if tenants:
        tenant_options = [t.replace('_', ' ') for t in tenants]
        selected_tenant = st.selectbox("Select a tenant:", ["-- Select a tenant --"] + tenant_options)

        if selected_tenant != "-- Select a tenant --":
            name = selected_tenant
            address = selected_address

            if st.button("Produce Tenant Report"):
                files = get_files_for_tenant(selected_address, selected_tenant.replace(' ', '_'), only_text=True)
                responses = ''
                for file in files:
                    metadata = get_metadata_for_file(BUCKET_NAME, file['Key'])
                    document_type = metadata.get('document_type', '').lower()
                    presigned_url = generate_presigned_url(BUCKET_NAME, file['Key'])
                    local_file_path = download_from_presigned_url(presigned_url)
                    file_encoding = detect_file_encoding(local_file_path)
                    with open(local_file_path, 'r', encoding=file_encoding) as f:
                        file_content = f.read()
                    file_content = re.sub(r'([a-zA-Z0-9])([a-zA-Z0-9])', r'\1 \2', file_content)
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo-0125",
                        messages=[
                            {
                                'role': 'system',
                                'content': (
                                    'You work for a detail-oriented property manager and are currently '
                                    'evaluating a prospective tenant. Your goal is to evaluate the tenant and '
                                    'determine whether they are a good fit for the property based only on the '
                                    'document provided. Pay close attention to key metrics like credit score, '
                                    'income level, and job stability. Be highly suspect of any red flags.'
                                )
                            },
                            {
                                'role': 'user',
                                'content': (
                                    f"Based on the following document from {name} with document type {document_type}, "
                                    "provide a concise summary of all meaningful aspects of the document for your "
                                    "manager. Be sure to highlight key numerical variables in your analysis. The "
                                    f"information you provide should help to determine whether {name} is a good fit "
                                    "as a tenant. Finally, provide commentary on whether you believe this tenant is "
                                    "a strong candidate.\n\n"
                                    f"```{file_content}```"
                                )
                            }
                        ],
                        temperature=0.0
                    )

                    response_text =  response.choices[0].message.content
                    response_text = response_text.replace('*', '\*').replace('_', '\_')
                    response_text = response_text.replace('\xa0', ' ')
                    response_text = response_text.replace('$', '\$')
                    st.write(response_text)
                    responses += (
                        f"The following is a report analyzing the document provided by {name} "
                        f"with document type {document_type}:\n\n{response_text}\n"
                    )
                    st.markdown(response_text)
                st.write(responses)

                # AI Tenant Evaluation Section
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo-0125",
                    messages=[
                        {
                            'role': 'system',
                            'content': (
                                'You are a highly detail-oriented property manager and are currently evaluating '
                                'a prospective tenant. Your goal is to evaluate the tenant and determine whether '
                                'they are a good fit for the property based on several reports provided to you. '
                                'Pay close attention to key metrics like credit score, income level, and job '
                                'stability. Be highly suspect of any red flags.'
                            )
                        },
                        {
                            'role': 'user',
                            'content': (
                                f"You are provided with several key summaries of the documents provided by the "
                                f"prospective tenant named {name} for a rental property located at {address}. "
                                "Based on these documents, write the following report with 4 sections:\n\n"
                                "Section 1 (Key Information): A summary of all the information provided to you.\n"
                                "Section 2 (Numerical Analysis): A summary of the key numerical variables in the documents.\n"
                                "Section 3 (Tenant Evaluation and Recommendation): A summary of whether you believe this tenant is a strong candidate or not.\n"
                                "Section 4 (Final Summary): Final bullet point summary of the most important metrics and information from your analysis.\n\n"
                                f"```{responses}```"
                            )
                        }
                    ],
                    temperature=0.0
                )
                response_text = response.choices[0].message.content
                response_text = response_text.replace('*', '\*').replace('_', '\_')
                response_text = response_text.replace('\xa0', ' ')
                response_text = response_text.replace('$', '\$')
                st.write(response_text)
        else:
            st.warning("Please select a tenant to proceed.")
    else:
        st.warning("No tenants available for this listing.")
        return

if __name__ == "__main__":
    # Initialize authenticator and session state variables
    if 'authenticator' not in st.session_state:
        st.session_state['authenticator'] = Authenticate("smartbidscookie3124", "smartbidskey3214", 30)
    if 'authentication_status' not in st.session_state:
        st.session_state['authentication_status'] = None
    if 'verified' not in st.session_state:
        st.session_state['verified'] = None

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
