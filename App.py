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
message_templates_sheet = sheet.worksheet("Message Templates")

# Load participant data into a DataFrame
participants_data = pd.DataFrame(participants_sheet.get_all_records())

# Load Message Templates sheet
message_templates_data = pd.DataFrame(message_templates_sheet.get_all_records())

# Load existing request IDs
existing_requests = set(pd.DataFrame(requests_sheet.get_all_values())[0].tolist())

# Custom Styling
# st.markdown("""
#     <style>
#     body, .stApp { background-color: #ffffff !important; color: #333333 !important; }
#     .stTextInput > div > div > input, .stSelectbox > div > div, .stTextArea > div > textarea {
#         border-radius: 10px; border: 1px solid #ccc; padding: 10px;
#     }
#     .stButton>button {
#         border-radius: 8px; background-color: #f8f9fa; color: #007bff; padding: 8px 12px;
#         border: 1px solid #007bff; font-size: 14px; cursor: pointer; transition: 0.3s;
#     }
#     .stButton>button:hover { background-color: #007bff; color: white; }
#     .error-message { color: #d9534f; font-weight: bold; margin-top: 10px; } /* Softer red */
#     .info-message { color: #5cb85c; font-weight: bold; margin-top: 10px; } /* Green message */

#     /* Ensure selected dropdown text is visible */
#     .stSelectbox > div[data-baseweb="select"] {
#         min-height: 40px !important; /* Ensures enough height */
#         overflow: visible !important; /* Prevents text from being hidden */
#     }

#     /* Adjust dropdown panel */
#     [data-baseweb="popover"] {
#         overflow: visible !important;
#     }

#     /* Sometimes, setting height to auto fixes it */
#     .stSelectbox > div[data-baseweb="select"] div {
#         height: auto !important;
#     }

#     /* Optional: Prevent dropdown from being cut off */
#     .st-ag {
#         overflow: visible !important;
#     }

#     /* Fix for Streamlit's internal layout bugs */
#     div[role="listbox"] {
#         max-height: 250px !important; /* Ensures dropdown items are visible */
#         overflow-y: auto !important; /* Allows scrolling */
#     }
#     </style>

# """, unsafe_allow_html=True)

st.markdown("""
    <style>
/* Fix dropdown content visibility */
.stSelectbox > div[data-baseweb="select"] {
    min-height: 45px !important; /* Ensures enough height */
    overflow: visible !important; /* Prevents text from being hidden */
    font-size: 16px !important; /* Ensures readability */
}

/* Adjust dropdown panel */
[data-baseweb="popover"] {
    overflow: visible !important;
}

/* Ensure the selected dropdown text is properly visible */
.stSelectbox > div[data-baseweb="select"] div {
    height: auto !important;
    padding: 10px !important;
}

/* Make field headers bold */
.stMarkdown h4, .stMarkdown h5, .stMarkdown h6, label {
    font-weight: bold !important;
    font-size: 16px !important;
    color: #333 !important;
}

/* Add space below the form header */
h1, h2 {
    margin-bottom: 15px !important;
}

/* Increase padding for form fields */
.stTextInput > div > div > input,
.stSelectbox > div > div,
.stTextArea > div > textarea {
    border-radius: 10px;
    border: 1px solid #ccc;
    padding: 12px;
    font-size: 14px;
}

/* Improve button styling */
.stButton>button {
    border-radius: 8px;
    background-color: #007bff;
    color: white;
    padding: 10px 15px;
    border: none;
    font-size: 14px;
    cursor: pointer;
    transition: 0.3s;
}

.stButton>button:hover {
    background-color: #0056b3;
}

/* Ensure consistent layout */
div[role="listbox"] {
    max-height: 250px !important;
    overflow-y: auto !important;
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

# Generate country code list (Without Flags)
def get_country_code_map():
    country_code_map = {}

    for cc in sorted(phonenumbers.COUNTRY_CODE_TO_REGION_CODE.keys()):
        regions = phonenumbers.COUNTRY_CODE_TO_REGION_CODE[cc]
        if regions:
            region = regions[0]  # Use the first region if multiple exist
            key = f"{region} (+{cc})"
            country_code_map[key] = str(cc)

    return country_code_map

# Get country data
country_code_map = get_country_code_map()
default_country = "IN (+91)"  # Default to India

# Function to get message based on template name
def get_message(template_name):
    message_row = message_templates_data[message_templates_data["Template Name"] == template_name]
    if not message_row.empty:
        return message_row.iloc[0]["Message"]
    return "⚠️ Please visit counter 23/24 at Welcome Point for further assistance with your request."

# Retrieve the specific message
assist_message = get_message("Reach Out to Add Credentials Message")
step_out_request_message = get_message("Step Out Request Default Message")

# Streamlit UI
st.title("🔹 Raise a Request")

# Input Variables
email = st.text_input("📧 Email ID", placeholder="Enter your Email ID")
email_verified = False
phone_verified = False
volunteer_category = None
name = None
phone_number = None
gender = None
show_forgot_email = False

# Check if email exists
if email and "forgot_email_clicked" not in st.session_state:
    matching_record = participants_data[participants_data["Email ID"] == email]
    if not matching_record.empty:
        volunteer_category = matching_record.iloc[0]["Volunteer Category"]
        name = matching_record.iloc[0]["Name"]
        gender = matching_record.iloc[0]["Gender"]
        phone_number = str(matching_record.iloc[0]["Phone Number"]).strip()

        # Auto-detect country code for stored numbers
        if not phone_number.startswith("+"):
            phone_number = f"+91{phone_number}"  # Assume India if no code

        phone_number = normalize_phone_number(phone_number)
        email_verified = True
    else:
        show_forgot_email = True
        st.error("❌ Email record does not exist in the database.")

# Show "Forgot my Email ID" button
if show_forgot_email and "forgot_email_clicked" not in st.session_state:
    if st.button("🔍 Forgot my Email ID"):
        st.session_state["forgot_email_clicked"] = True

# **Phone Input - Without Flags**
if st.session_state.get("forgot_email_clicked", False):
    col1, col2 = st.columns([1.5, 3])  

    with col1:
        selected_country = st.selectbox("🌍 Select Country Code", list(country_code_map.keys()), index=list(country_code_map.keys()).index(default_country))
        country_code = country_code_map[selected_country]

    with col2:
        raw_phone = st.text_input("📞 Phone Number", placeholder="Enter phone number without country code")

    # Validate and normalize input
    if raw_phone:
        normalized_input_number = normalize_phone_number(f"+{country_code}{raw_phone}")

        # Normalize stored phone numbers for verification
        participants_data["Normalized Phone Number"] = participants_data["Phone Number"].astype(str).apply(
            lambda num: normalize_phone_number(f"+91{num}") if not num.startswith("+") else normalize_phone_number(num)
        )

        phone_match = participants_data[participants_data["Normalized Phone Number"] == normalized_input_number]

        if not phone_match.empty:
            volunteer_category = phone_match.iloc[0]["Volunteer Category"]
            name = phone_match.iloc[0]["Name"]
            gender = phone_match.iloc[0]["Gender"]
            email = phone_match.iloc[0]["Email ID"]
            phone_verified = True
            st.success("✅ Now you can fill the request type and description to submit the form.")
        else:
            st.error("❌ Phone number does not exist in the database.")
            st.warning(assist_message)  # Use the dynamically fetched message
            

# Define request type options based on participant type
request_options = ["", "Seva Team", "Health Team", "Sahaya (Support) Team", "Others"]
if volunteer_category == "Long Term Department Support":
    request_options.insert(2, "Accommodation Team")

# Initialize session state for dynamic UI updates
if "selected_request_type" not in st.session_state:
    st.session_state.selected_request_type = ""

if "sub_category_options" not in st.session_state:
    st.session_state.sub_category_options = []

# Initialize session state for date fields
if "from_date" not in st.session_state:
    st.session_state.from_date = None

if "to_date" not in st.session_state:
    st.session_state.to_date = None

# Function to reset form state
def reset_form():
    st.session_state.request_type = ""
    st.session_state.sub_category = ""
    st.session_state.description = ""
    st.session_state.step_out_message = False  # Hide message
    st.session_state.linga_seva_message = False
    st.session_state.extension_request_message = False
    st.session_state.clear_form = False
    st.session_state.from_date = None  # Reset From Date
    st.session_state.to_date = None    # Reset To Date

# Initialize session state for step-out message
if "step_out_message" not in st.session_state:
    st.session_state.step_out_message = False

if "linga_seva_message" not in st.session_state:
    st.session_state.linga_seva_message = False

if "extension_request_message" not in st.session_state:
    st.session_state.extension_request_message = False

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
    st.session_state.linga_seva_message = False
    st.session_state.extension_request_message = False

    # Define dynamic sub-category options
    if request_type == "Seva Team":
        st.session_state.sub_category_options = ["Seva Affecting Health", "Seva Change", "Linga Seva", "Devi Seva", "Prana Danam", "Adi Yogi Arpanam", "Others"]
        if volunteer_category == "Long Term Department Support":
            st.session_state.sub_category_options.insert(0, "Meet Seva Team")
    
    elif request_type == "Sahaya (Support) Team" and volunteer_category == "Long Term Department Support":
        st.session_state.sub_category_options = ["Meet Sahaya Team", "Step out of Ashram", "3 days Silence", "Extension Request", "Others"]
    
    else:
        st.session_state.sub_category_options = []

# Display Sub Category Dropdown only if options exist
sub_category = None
if st.session_state.sub_category_options:
    sub_category = st.selectbox("📌 Sub Category", [""] + st.session_state.sub_category_options, index=0, key="sub_category")

# Show information message based on selected sub-category
if sub_category == "Step out of Ashram":
    st.session_state.step_out_message = True
    st.session_state.linga_seva_message = False
    st.session_state.extension_request_message = False
elif sub_category == "Linga Seva":
    st.session_state.step_out_message = False
    st.session_state.linga_seva_message = True
    st.session_state.extension_request_message = False
elif sub_category == "Extension Request":
    st.session_state.step_out_message = False
    st.session_state.linga_seva_message = False
    st.session_state.extension_request_message = True
else:
    # Hide all messages when another sub-category is selected
    st.session_state.step_out_message = False
    st.session_state.linga_seva_message = False
    st.session_state.extension_request_message = False


# Show Step-Out Message
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

# Show Linga Seva Message
if st.session_state.linga_seva_message:
    st.markdown(
        """
        <div style='color: #555555; background-color: #f8f9fa; padding: 12px; border-radius: 8px; font-size: 14px;'>
            <b>⚠️ Applicable for both 5 days and 10 days Linga Seva</b>
        </div>
        """,
        unsafe_allow_html=True
    )

# Show Extension Request Message
if st.session_state.extension_request_message:
    st.markdown(
        """
        <div style='color: #555555; background-color: #f8f9fa; padding: 12px; border-radius: 8px; font-size: 14px;'>
            <b>⚠️ Please mention the date until which you wish to extend and the reason why.</b>
        </div>
        """,
        unsafe_allow_html=True
    )

# Define the sub-categories that require date selection
date_required_sub_categories = {
    "Linga Seva", "Devi Seva", "Prana Danam", "Adi Yogi Arpanam", 
    "Step out of Ashram", "3 days Silence", "Extension Request"
}

# Set default date values (even if hidden)
if sub_category in date_required_sub_categories:
    st.session_state.from_date = datetime.today()
    st.session_state.to_date = datetime.today()

    if sub_category == "Extension Request":
        # Show "To Date" picker in full width for "Extension Request"
        st.session_state.to_date = st.date_input("📅 To Date", 
            value=st.session_state.to_date, format="DD/MM/YYYY")
    else:
        # Use two-column layout for other subcategories
        col1, col2 = st.columns(2)

        with col1:
            st.session_state.from_date = st.date_input("📅 From Date", 
                value=st.session_state.from_date, format="DD/MM/YYYY")

        with col2:
            st.session_state.to_date = st.date_input("📅 To Date", 
                value=st.session_state.to_date, format="DD/MM/YYYY")

else:
    st.session_state.from_date = None
    st.session_state.to_date = None

# Description (Mandatory)
description = st.text_area("📝 Description of your request", key="description")

import random
import string

# Function to generate a unique request ID in incremental order
def generate_unique_request_id(volunteer_category):
    # Define request prefix mapping
    request_prefix = {
        "Ashram Volunteer": "AV",
        "Short Term Department Support": "STV",
        "Long Term Department Support": "LTV"
    }.get(volunteer_category, "REQ")

    # Add "REQ-" to the prefix
    full_prefix = f"REQ-{request_prefix}"

    # Extract existing numeric parts of request IDs for this category
    existing_numbers = sorted([
        int(request_id.replace(full_prefix, "")) for request_id in existing_requests 
        if request_id.startswith(full_prefix) and request_id.replace(full_prefix, "").isdigit()
    ])

    # Determine the next available number (incremental approach)
    next_number = 1  # Start from 00001

    for num in existing_numbers:
        if num == next_number:
            next_number += 1  # Move to the next available number
        else:
            break  # Found a gap, use this number

    # If we reach 99999, switch to alphanumeric fallback
    if next_number > 99999:
        for _ in range(10000):  # Try up to 10,000 times to find a unique alphanumeric ID
            random_alnum = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            request_id = f"{full_prefix}{random_alnum}"
            if request_id not in existing_requests:
                return request_id
        return f"{full_prefix}XXXXX"  # Fallback if all alphanumeric options are exhausted

    # Format the number as a 5-digit string and return
    request_id = f"{full_prefix}{next_number:05d}"
    return request_id


# Submit Button
if st.button("Submit Request"):
    if not (email_verified or phone_verified):
        st.error("⚠️ Please enter a valid Email ID or Phone Number.")
    elif not request_type or request_type == "":
        st.error("⚠️ Please select a Request Type.")
    elif st.session_state.sub_category_options and (not sub_category or sub_category == ""):
        st.error("⚠️ Please select a Sub Category.")
    elif sub_category in date_required_sub_categories and (not st.session_state.from_date or not st.session_state.to_date):
        st.error("⚠️ Please select both From Date and To Date.")
    elif not description.strip():
        st.error("⚠️ Please enter a description.")
    else:
        request_id = generate_unique_request_id(volunteer_category)

        # Save to Google Sheet
        requests_sheet.append_row([
            request_id,
            name,  # Name from Volunteer Details
            gender,  # Gender
            email,  # Email ID
            phone_number,  # Phone Number
            volunteer_category,
            request_type,
            sub_category if sub_category else "None",
            st.session_state.from_date.strftime("%d/%m/%Y") if st.session_state.from_date else "None",  # Store in dd/mm/yyyy format
            st.session_state.to_date.strftime("%d/%m/%Y") if st.session_state.to_date else "None",
            description,
            str(datetime.now())
        ])

        # Display different messages based on the sub-category
        if sub_category == "Step out of Ashram":
            # Format the message with request ID
            formatted_message = step_out_request_message.replace("{request_id}", request_id)
            # Force a newline before "Your request ID"
            formatted_message = formatted_message.replace("Your request ID:", "\n\nYour request ID:")
            st.success(formatted_message)
            
            # st.success(
            #     "🔹 Please request your department coordinator to send an approval email for your step out request to "
            #     "**overseas.volunteers@ishafoundation.org**, for us to process it further.\n\n"
            #     f"Your request ID: **{request_id}**"
            # )
        else:
            st.success(
                f"✅ **We have received your request (Request ID: {request_id}).**\n\n"
                "The respective team will get back to you shortly."
            )

        time.sleep(21)
        # Set flag to clear form on next render
        st.session_state.clear_form = True
        st.rerun()  # Force rerun to refresh form inputs
