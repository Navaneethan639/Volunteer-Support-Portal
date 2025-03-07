import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time
import random
import string
import json
import emoji
import phonenumbers
from phonenumbers.phonenumberutil import region_code_for_country_code

# Google Sheets API Setup
SHEET_URL = "https://docs.google.com/spreadsheets/d/17Jf186s0G5uQrT6itt8KuiP9GhJqVtyqREyc_kYFS9M/edit?gid=0#gid=0"
SERVICE_ACCOUNT_FILE = "service_account.json"

# st.write("🔍 Checking credentials...")

# Verify if Streamlit secrets are correctly loaded
if "gcp_service_account" not in st.secrets:
    # st.error("❌ `gcp_service_account` is missing in Streamlit secrets!")
    st.stop()

# Print loaded keys for debugging (DO NOT print private key)
creds_dict = st.secrets["gcp_service_account"]
# st.write("✅ Service account loaded:", creds_dict["client_email"])

# Define Google API scopes
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

try:
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    # st.success("✅ Authentication successful!")
except Exception as e:
    st.error(f"❌ Authentication failed: {e}")
    st.stop()

# Google Sheets Authentication
#scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
#creds = Credentials.from_service_account_info(json.loads(json.dumps(creds_dict)))
#creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scope)
#client = gspread.authorize(creds)

# Load the Participants and Requests sheets
sheet = client.open_by_url(SHEET_URL)
# sheet = client.open('Volunteer Support Portal')
participants_sheet = sheet.worksheet("Volunteer Details")
requests_sheet = sheet.worksheet("Requests")

# Load participant data into a DataFrame
participants_data = pd.DataFrame(participants_sheet.get_all_records())

# Load existing request IDs
existing_requests = set(pd.DataFrame(requests_sheet.get_all_values())[0].tolist())

# Custom Styling
st.markdown("""
    <style>
    body, .stApp { background-color: #ffffff !important; color: #333333 !important; }
    .stTextInput > div > div > input, .stSelectbox > div > div, .stTextArea > div > textarea {
        border-radius: 10px; border: 1px solid #ccc; padding: 10px;
    }
    .stButton>button {
        border-radius: 8px; background-color: #f8f9fa; color: #007bff; padding: 8px 12px;
        border: 1px solid #007bff; font-size: 14px; cursor: pointer; transition: 0.3s;
    }
    .stButton>button:hover { background-color: #007bff; color: white; }
    .error-message { color: #d9534f; font-weight: bold; margin-top: 10px; } /* Softer red */
    .info-message { color: #5cb85c; font-weight: bold; margin-top: 10px; } /* Green message */

    /* Ensure selected dropdown text is visible */
    .stSelectbox > div[data-baseweb="select"] {
        min-height: 40px !important; /* Ensures enough height */
        overflow: visible !important; /* Prevents text from being hidden */
    }

    /* Adjust dropdown panel */
    [data-baseweb="popover"] {
        overflow: visible !important;
    }

    /* Sometimes, setting height to auto fixes it */
    .stSelectbox > div[data-baseweb="select"] div {
        height: auto !important;
    }

    /* Optional: Prevent dropdown from being cut off */
    .st-ag {
        overflow: visible !important;
    }

    /* Fix for Streamlit's internal layout bugs */
    div[role="listbox"] {
        max-height: 250px !important; /* Ensures dropdown items are visible */
        overflow-y: auto !important; /* Allows scrolling */
    }
    </style>

""", unsafe_allow_html=True)

# Function to normalize phone numbers to E.164 format
def normalize_phone_number(phone_number, country_code="IN"):
    try:
        parsed_number = phonenumbers.parse(phone_number, country_code)
        if not phonenumbers.is_valid_number(parsed_number):
            return None
        return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        return None

# Generate dynamic country code list with flags
def get_country_flag(country_code):
    try:
        return emoji.emojize(f":flag-{country_code.lower()}:", language='alias')
    except:
        return "🏳️"

country_code_map = {
    f"{get_country_flag(region_code_for_country_code(cc))} {region_code_for_country_code(cc)} (+{cc})": cc
    for cc in sorted(phonenumbers.COUNTRY_CODE_TO_REGION_CODE.keys())
    if region_code_for_country_code(cc)  # Ensure valid country codes only
}

# Set default country as India (+91)
default_country = "🇮🇳 IN (+91)"
default_country_code = "91"

# Streamlit UI
st.title("🔹 Raise a Request")

# Input Variables
email = st.text_input("📧 Email ID", placeholder="Enter your Email ID")
email_verified = False
phone_verified = False
volunteer_category = None
name = None
phone_number = None
show_forgot_email = False

# Check if email exists
if email and "forgot_email_clicked" not in st.session_state:
    matching_record = participants_data[participants_data["Email ID"] == email]
    if not matching_record.empty:
        volunteer_category = matching_record.iloc[0]["Volunteer Category"]
        name = matching_record.iloc[0]["Name"]
        phone_number = str(matching_record.iloc[0]["Phone Number"]).strip()
        
        # Auto-detect country code for stored numbers
        if phone_number.startswith("+"):
            phone_number = normalize_phone_number(phone_number)
        else:
            phone_number = normalize_phone_number(phone_number, "IN")  # Assume India if no code

        email_verified = True
    else:
        show_forgot_email = True
        st.error("❌ Email record does not exist in the database.")

# Show "Forgot my Email ID" button
if show_forgot_email and "forgot_email_clicked" not in st.session_state:
    if st.button("🔍 Forgot my Email ID"):
        st.session_state["forgot_email_clicked"] = True

# Phone Input with **Flags + Country Code Selector**
if st.session_state.get("forgot_email_clicked", False):
    col1, col2 = st.columns([1.2, 2.5])  # Adjust widths

    with col1:
        selected_country = st.selectbox("🌍 Country Code", list(country_code_map.keys()), index=list(country_code_map.keys()).index(default_country))
        country_code = country_code_map[selected_country]

    with col2:
        raw_phone = st.text_input("📞 Phone Number", placeholder="Enter number")

    if raw_phone:
        normalized_input_number = normalize_phone_number(raw_phone, country_code)

        # Normalize stored phone numbers for verification
        participants_data["Normalized Phone Number"] = participants_data["Phone Number"].astype(str).apply(
            lambda num: normalize_phone_number(num, "IN") if not num.startswith("+") else normalize_phone_number(num)
        )

        phone_match = participants_data[participants_data["Normalized Phone Number"] == normalized_input_number]

        if not phone_match.empty:
            volunteer_category = phone_match.iloc[0]["Volunteer Category"]
            name = phone_match.iloc[0]["Name"]
            email = phone_match.iloc[0]["Email ID"]
            phone_verified = True
            st.success("✅ Now you can fill the request type and description to submit the form.")
        else:
            st.error("❌ Phone number does not exist in the database.")

# Define request type options based on participant type
request_options = ["", "Seva Team", "Health Team", "Sahaya (Support) Team", "Others"]
if volunteer_category == "Long Term Department Support":
    request_options.insert(2, "Accommodation Team")

# Initialize session state for dynamic UI updates
if "selected_request_type" not in st.session_state:
    st.session_state.selected_request_type = ""

if "sub_category_options" not in st.session_state:
    st.session_state.sub_category_options = []

# Function to reset form state
def reset_form():
    st.session_state.request_type = ""
    st.session_state.sub_category = ""
    st.session_state.description = ""
    st.session_state.step_out_message = False  # Hide message
    st.session_state.clear_form = False

# Initialize session state for step-out message
if "step_out_message" not in st.session_state:
    st.session_state.step_out_message = False

# Initialize form reset flag
if "clear_form" not in st.session_state:
    st.session_state.clear_form = False

# Reset form fields before rendering widgets
if st.session_state.clear_form:
    reset_form()

# Request Type Dropdown
request_type = st.selectbox("📌 I want to reach out to:", request_options, index=0, key="request_type")

# Update session state on request type selection
if request_type != st.session_state.selected_request_type:
    st.session_state.selected_request_type = request_type
    st.session_state.step_out_message = False  # Hide message when request type changes

    # Define dynamic sub-category options
    if request_type == "Seva Team":
        st.session_state.sub_category_options = ["Seva Affecting Health", "Seva Change", "Others"]
        if volunteer_category == "Long Term Department Support":
            st.session_state.sub_category_options.insert(0, "Meet Seva Team")
    
    elif request_type == "Sahaya (Support) Team" and volunteer_category == "Long Term Department Support":
        st.session_state.sub_category_options = ["Meet Sahaya Team", "Step out of Ashram", "Others"]
    
    else:
        st.session_state.sub_category_options = []

# Display Sub Category Dropdown only if options exist
sub_category = None
if st.session_state.sub_category_options:
    sub_category = st.selectbox("📌 Sub Category", [""] + st.session_state.sub_category_options, index=0, key="sub_category")

# Show information message for "Step out of Ashram"
if sub_category == "Step out of Ashram":
    st.session_state.step_out_message = True
else:
    st.session_state.step_out_message = False  # Hide message for other sub-categories

# Show step-out message in proper format
if st.session_state.step_out_message:
    st.markdown(
        """
        <div style='color: #555555; background-color: #f8f9fa; padding: 12px; border-radius: 8px; font-size: 14px;'>
            <b style="display: block; margin-bottom: 5px;">⚠️ Please raise the request at least <u>72 hrs before the travel date</u>:</b>
            <ul style="padding-left: 20px; margin: 5px 0;">
                <li>📅 <b>Mention the Dates of Departure & Expected Return</b></li>
                <li>📝 <b>Specify the Reason for travel in the description</b></li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True
    )

# Description (Mandatory)
description = st.text_area("📝 Description of your request", key="description")

# Function to generate a unique request ID
def generate_unique_request_id(volunteer_category):
    request_prefix = {
        "Ashram Volunteer": "AV",
        "Short Term Department Support": "STV",
        "Long Term Department Support": "LTV"
    }.get(volunteer_category, "REQ")

    # Attempt to generate a unique 5-digit numeric ID
    for _ in range(10000):
        random_number = random.randint(10000, 99999)
        request_id = f"{request_prefix}{random_number}"
        if request_id not in existing_requests:
            return request_id

    # If all numeric IDs are taken, generate a 5-character alphanumeric ID
    for _ in range(10000):
        random_alnum = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        request_id = f"{request_prefix}{random_alnum}"
        if request_id not in existing_requests:
            return request_id

    return f"{request_prefix}XXXXX"  # Fallback if all combinations are exhausted

# Submit Button
if st.button("Submit Request"):
    if not (email_verified or phone_verified):
        st.error("⚠️ Please enter a valid Email ID or Phone Number.")
    elif not request_type or request_type == "":
        st.error("⚠️ Please select a Request Type.")
    elif st.session_state.sub_category_options and (not sub_category or sub_category == ""):
        st.error("⚠️ Please select a Sub Category.")
    elif not description.strip():
        st.error("⚠️ Please enter a description.")
    else:
        request_id = generate_unique_request_id(volunteer_category)

        # Save to Google Sheet
        requests_sheet.append_row([
            request_id,
            name,  # Name from Volunteer Details
            email,  # Email ID
            phone_number,  # Phone Number
            volunteer_category,
            request_type,
            sub_category if sub_category else "None",
            description,
            str(datetime.now())
        ])

        # Display different messages based on the sub-category
        if sub_category == "Step out of Ashram":
            st.success(
                "🔹 Please request your department coordinator to send an approval email for your step out request to "
                "**overseas.volunteers@ishafoundation.org**, for us to process it further.\n\n"
                f"Your request ID: **{request_id}**"
            )
        else:
            st.success(
                f"✅ **We have received your request (Request ID: {request_id}).**\n\n"
                "The respective team will get back to you shortly."
            )

        time.sleep(21)
        # Set flag to clear form on next render
        st.session_state.clear_form = True
        st.rerun()  # Force rerun to refresh form inputs
