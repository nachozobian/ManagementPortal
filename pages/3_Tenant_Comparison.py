import streamlit as st
import pandas as pd
import plotly.express as px
import sys
from utils import fetch_created_listings, get_tenants_for_address, get_metadata_for_file, list_files_for_tenant


def calculate_rent_to_income(rent, income):
    """Calculate rent-to-income ratio."""
    try:
        income = float(income)
        if income > 0:
            return round((rent / income) * 100, 2)
        return None
    except (ValueError, TypeError):
        return None
    

def main():
    st.title('Tenant Comparison Dashboard')

    # Analyze Candidates for an Address Section
    st.subheader("Compare Tenants for a Listing")
    available_listings = fetch_created_listings()  # Changed from fetch_created_listings() to fetch_listings()
    if not available_listings:
        st.warning("No listings available at the moment.")
        return

    selected_address = st.selectbox("Select a listing:", available_listings)
    tenants = get_tenants_for_address(selected_address)
    if not tenants:
        st.warning("No tenants available for this listing.")
        return

    # Tenant selection (multiple)
    selected_tenants = st.multiselect("Select tenants to compare:", tenants)
    if not selected_tenants:
        st.warning("Please select at least two tenants to compare.")
        return

    # Initialize DataFrame to store comparison data
    comparison_data = []

    # Fetch and organize data for each tenant
    for tenant in selected_tenants:
        tenant_data = {'Tenant Name': tenant.replace('_', ' ')}
        file_names, files = list_files_for_tenant(selected_address, tenant)
        
        # Extract metrics from metadata
        for file in files:
            metadata = get_metadata_for_file(file['Key'])
            document_type = metadata.get('document_type', '').lower()
            
            if document_type == 'credit score':
                tenant_data['Credit Score'] = metadata.get('credit score', 'N/A')
            elif document_type == 'income verification':
                tenant_data['Monthly Income'] = metadata.get('monthly income', 'N/A')
            elif document_type == 'references':
                tenant_data['References'] = metadata.get('references', 'N/A')

        # Calculating custom metrics like rent-to-income ratio
        rent = 1000  # Replace this with actual rent value if available
        tenant_data['Rent-to-Income Ratio (%)'] = calculate_rent_to_income(rent, tenant_data.get('Monthly Income', 0))
        comparison_data.append(tenant_data)

    # Create DataFrame for visualization
    df = pd.DataFrame(comparison_data)

    # Displaying data in a table
    st.write("## Comparison Table")
    st.dataframe(df)

    # Visualizing Credit Score comparison
    if 'Credit Score' in df.columns:
        st.write("## Credit Score Comparison")
        fig = px.bar(df, x='Tenant Name', y='Credit Score', title='Credit Score Comparison', text='Credit Score')
        st.plotly_chart(fig)

    # Visualizing Rent-to-Income Ratio comparison
    if 'Rent-to-Income Ratio (%)' in df.columns:
        st.write("## Rent-to-Income Ratio Comparison")
        fig = px.bar(df, x='Tenant Name', y='Rent-to-Income Ratio (%)', title='Rent-to-Income Ratio Comparison', text='Rent-to-Income Ratio (%)')
        st.plotly_chart(fig)

if __name__ == "__main__":
    main()
