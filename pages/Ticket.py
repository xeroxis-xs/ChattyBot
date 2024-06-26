import os
import time
import markdown2
import requests
from io import BytesIO
from datetime import datetime
import pytz
from dotenv import load_dotenv
import streamlit as st
from msal import ConfidentialClientApplication

from Narelle import Narelle
from utils.DBConnector import DBConnector
from texts import LongText
from utils.Logger import setup_logger
from utils.Email import AzureEmailClient


# Utility Functions
def get_time():
    curr_time = {
        "text": datetime.now(st.session_state.tz).strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp": datetime.now(st.session_state.tz).timestamp()
    }
    return curr_time


def streaming_respond(msg):
    for word in msg.split(" "):
        yield word + " "
        time.sleep(0.05)


def logout():
    st.query_params.clear()
    del st.session_state.user
    del st.session_state.email
    del st.session_state.auth_code
    st.session_state.all_messages = None
    st.rerun()


def unauthorise(progress_text, error_msg):
    st.query_params.clear()
    del st.session_state.user
    del st.session_state.email
    del st.session_state.auth_code
    progress_bar.progress(100, text=progress_text)

    st.error(error_msg)
    st.button("Retry")

    time.sleep(2)
    progress_bar.empty()


def get_auth_url(app):
    auth_url = app.get_authorization_request_url(
        scopes=["User.Read"],
    )
    return auth_url


def get_token_from_code(app, auth_code):
    result = app.acquire_token_by_authorization_code(
        auth_code,
        scopes=["User.Read"],
    )
    return result


def get_user_photo(user_object_id, access_token):
    # Make a GET request to the Microsoft Graph API
    headers = {"Authorization": "Bearer " + access_token}
    response = requests.get(f"https://graph.microsoft.com/v1.0/users/{user_object_id}/photo/$value", headers=headers)
    if response.status_code == 200:
        # Convert the binary data to a BytesIO object
        image_data = BytesIO(response.content)
        return image_data
    else:
        return None


def get_tickets(student_email=None, instructor_email=None, status="Open"):
    if student_email:
        return list(tickets_collection.find({"student_email": student_email, "status": status}))
    elif instructor_email:
        return list(tickets_collection.find({"instructor_email": instructor_email, "status": status}))
    else:
        return list(tickets_collection.find())


def get_ticket(ticket_id):
    return tickets_collection.find_one({"_id": ticket_id})


def get_conv_messages(selected_ticket):
    try:
        conv_id = selected_ticket['conversation_id']
        return st.session_state.mongodb.conversations.find_one({"_id": conv_id})['messages']
    except Exception:
        st.error(f"Error fetching conversation history")


def add_message(ticket_id, sender_name, sender_email, message):
    new_message = {
        "sender_name": sender_name,
        "sender_email": sender_email,
        "message": message,
        "timestamp": get_time()
    }
    tickets_collection.update_one(
        {"_id": ticket_id},
        {"$push": {"messages": new_message}}
    )


def update_ticket_status(ticket_id, status):
    tickets_collection.update_one({"_id": ticket_id}, {"$set": {"status": status}})


def convert_markdown_to_html(markdown_text):
    return markdown2.markdown(markdown_text)


def display_message(message, sender_name, avatar):
    dt_object = datetime.fromtimestamp(message['timestamp']['timestamp'])
    formatted_date = dt_object.strftime('%d %b %I:%M %p')
    with st.chat_message(sender_name, avatar=avatar):
        formatted_name = sender_name.replace("#", "")
        st.markdown(f"**{formatted_name}**")
        st.markdown(f"{message['message']}")
        st.caption(f"{formatted_date}")


# Main function to display ticket messages
def display_ticket_messages(selected_ticket):
    user_email = st.session_state.email

    for message in selected_ticket['messages']:
        sender_email = message['sender_email']

        # User view his own message
        if sender_email == user_email:
            display_message(message, st.session_state.formatted_name, st.session_state.user_photo)
        # User view other's message
        else:
            display_message(message, message['sender_name'].replace("#", ""), None)


def send_new_msg_email(selected_ticket, recipient_email, recipient_name, new_message):
    try:
        # Read HTML template
        new_msg_html_template = email_client.read_html_template("email_template/new_message_email_template.html")

        # Convert markdown to HTML
        converted_message_html = convert_markdown_to_html(new_message)

        # Customize HTML content
        html_body = new_msg_html_template.format(
            recipient_name=selected_ticket['student_name'] if st.session_state.user_type == "instructor" else
            selected_ticket['instructor_name'],
            sender_name=st.session_state.user,
            latest_message=converted_message_html,
            streamlit_app_url="https://asknarelle.azurewebsites.net/"
        )

        # Send email notification
        subject = f"[AskNarelle] New message in Ticket {selected_ticket['_id']}"
        plain_text_body = new_message
        from_email = "DoNotReply@140197c9-8f19-4c8a-9bb4-23adfc6600ef.azurecomm.net"
        message = email_client.draft_email(
            subject,
            html_body,
            plain_text_body,
            [recipient_email],
            [recipient_name],
            from_email
        )
        email_client.send_email(message)
    except Exception as e:
        st.error(f"Error sending email notification: {e}")


def send_update_ticket_status_email(selected_ticket, status):
    try:
        # Read HTML template
        status_update_html_template = email_client.read_html_template("email_template/status_update_for_email_template.html")

        # Customize HTML content
        html_body = status_update_html_template.format(
            ticket_id=selected_ticket['_id'],
            ticket_title=selected_ticket['title'],
            status=status,
            streamlit_app_url="https://asknarelle.azurewebsites.net/"
        )

        # Send email notification
        subject = f"[AskNarelle] Status Update for Ticket {selected_ticket['_id']}"
        plain_text_body = f"Status of the Ticket {selected_ticket['_id']} has been marked as {status}"
        from_email = "DoNotReply@140197c9-8f19-4c8a-9bb4-23adfc6600ef.azurecomm.net"
        message = email_client.draft_email(
            subject,
            html_body,
            plain_text_body,
            [selected_ticket['student_email'], selected_ticket['instructor_email']],
             [selected_ticket['student_name'], selected_ticket['instructor_name']],
            from_email
        )
        email_client.send_email(message)
    except Exception as e:
        st.error(f"Error sending email notification: {e}")


# Main Program

# Load Environment Variables
load_dotenv(override=True)
DB_HOST = os.environ['CA_MONGO_DB_HOST']
DB_NAME = os.environ['CA_MONGO_DB']
CLIENT_ID = os.environ['APP_REG_CLIENT_ID']
AUTHORITY = os.environ['APP_REG_AUTHORITY']
CLIENT_SECRET = os.environ['APP_REG_CLIENT_SECRET']

# Initialise Logger
logger = setup_logger()
logger.info("Starting AskNarelle...")

# Initialise App Registration
app = ConfidentialClientApplication(
    client_id=CLIENT_ID,
    authority=AUTHORITY,
    client_credential=CLIENT_SECRET,
)

# Initialise Email Client
email_client = AzureEmailClient()

logger.info("----------- New state ----------")

# Initialise Streamlit App
st.set_page_config(page_title='AskNarelle - Your friendly course assistant', page_icon="🙋‍♀️")
st.title("🎫 Support Ticket")
st.write(f"For queries related to {os.environ['COURSE_NAME']}")

informed_consent_form = st.empty()
st.session_state.tz = pytz.timezone("Asia/Singapore")
chat_avatars = {
    "instructor": "imgs/instructor_user_avatar.jpg",
    "user": {"Male": "imgs/male_user_avatar.jpg",
             "Female": "imgs/female_user_avatar.jpg"}
}

# Initialise session state if not already initialised
if "user" not in st.session_state:
    st.session_state.user = None
if "email" not in st.session_state:
    st.session_state.email = None
if "auth_code" not in st.session_state:
    st.session_state.auth_code = None

# User has not signed in
if st.session_state.user is None:
    st.session_state.auth_code = st.query_params.get("code")
    # Clear query parameters
    st.query_params.clear()
    if st.session_state.auth_code is None:
        with informed_consent_form.container():
            # Display consent form
            with st.container(height=300):
                st.markdown(LongText.TERMS_OF_USE)
            st.checkbox(LongText.CONSENT_ACKNOWLEDGEMENT, key="agree_check")
            cols = st.columns(4)

            # Display buttons
            with cols[0]:
                btn_agree = st.button("Agree and Proceed", disabled=not st.session_state.agree_check)
            with cols[1]:
                btn_inform_consent = st.link_button("Download Consent", url=os.environ['INFORM_CONSENT_SC1015'])

        # If user agrees to the terms of use
        if btn_agree:
            informed_consent_form.empty()
            auth_url = get_auth_url(app)
            st.markdown(
                f"To prevent unauthorised usage and abuse of the system, we will need you to verify that you are an NTU "
                f"student. Please follow the verification process below to continue...")
            st.markdown(f'<a href="{auth_url}" target="_self">Proceed to Verification</a>', unsafe_allow_html=True)
            progress_bar = st.progress(0, text="Please click the link above to verify.")

    else:
        progress_bar = st.progress(20, text="Authenticating...")
        result = get_token_from_code(app, st.session_state.auth_code)
        # If login is successful
        if "access_token" in result:
            progress_bar.progress(50, text="Retrieving and checking profile...")

            # Get user profile
            st.session_state.user_photo = get_user_photo(result['id_token_claims']['oid'], result['access_token'])
            st.session_state.user = result['id_token_claims']['name']
            st.session_state.email = result['id_token_claims']['preferred_username']
            st.session_state.formatted_name = st.session_state.user.replace("#", "")

            logger.info(st.session_state.user)

            # Connect to MongoDB
            st.session_state.mongodb = DBConnector(DB_HOST).get_db(DB_NAME)
            allowed_users = st.session_state.mongodb.users_permission.find_one({"status": "allowed"})['users']
            blocked_users = st.session_state.mongodb.users_permission.find_one({"status": "blocked"})['users']

            if st.session_state.email in blocked_users:
                unauthorise(progress_text="Unauthorised user...", error_msg="This account has been blocked")

            elif "ntu.edu.sg" in st.session_state.email[-10:] or st.session_state.email in allowed_users:

                progress_bar.progress(70, text="Waking up Narelle...")
                LLM_DEPLOYMENT_NAME = os.environ['AZURE_OPENAI_DEPLOYMENT_NAME']
                LLM_MODEL_NAME = os.environ['AZURE_OPENAI_MODEL_NAME']
                st.session_state.narelle = Narelle(deployment_name=LLM_DEPLOYMENT_NAME, model_name=LLM_MODEL_NAME)

                # Initializing Conversations
                conversation = {
                    "stime": get_time(),
                    "user": st.session_state.user,
                    "email": st.session_state.email,
                    "messages": [],
                    "last_interact": get_time(),
                    "llm_deployment_name": os.environ['AZURE_OPENAI_DEPLOYMENT_NAME'],
                    "llm_model_name": os.environ['AZURE_OPENAI_MODEL_NAME'],
                    "vectorstore_index": os.environ['CA_AZURE_VECTORSTORE_INDEX']
                }

                # Initialize conversation in MongoDB
                st.session_state.conv_id = st.session_state.mongodb.conversations.insert_one(
                    conversation).inserted_id

                # Initialize AI messages
                st.session_state.all_messages = [
                    {"role": "ai", "content": f"{LongText.NARELLE_GREETINGS}", "recorded_on": get_time()}]

                progress_bar.progress(100, text="Narelle is Ready!")
                time.sleep(1)
                progress_bar.empty()
                st.rerun()

            else:
                unauthorise(progress_text="Unauthorised user...",
                            error_msg="Please verify using your NTU email address")

        # Login failed
        else:
            st.write(result.get("error"))
            st.write(result.get("error_description"))
            st.write(result.get("correlation_id"))  # You may need this when reporting a bug

# User has signed in
else:
    # Get tickets collection from MongoDB
    tickets_collection = st.session_state.mongodb.tickets
    # Set user type based on domain
    domain = st.session_state.email.split("@")[1]

    # Display sidebar
    with st.sidebar:
        st.header("Tickets")
        ticket_status_filter = st.radio("Filter ticket status: ", ["Open", "Resolved"], horizontal=True)

        if domain == "e.ntu.edu.sg":
            st.session_state.user_type = "student"
            tickets = get_tickets(student_email=st.session_state.email, status=ticket_status_filter)
        else:
            st.session_state.user_type = "instructor"
            tickets = get_tickets(instructor_email=st.session_state.email, status=ticket_status_filter)

        ticket_ids = [ticket["_id"] for ticket in tickets]
        selected_ticket_id = st.selectbox("Select a ticket to view", ticket_ids)
        selected_ticket = get_ticket(selected_ticket_id)

        # Student only can mark ticket as resolved, Instructor can mark ticket as resolved or reopen ticket
        # Display button to change ticket status

        if selected_ticket:
            # Display Mark as Resolved button only if status Open
            if selected_ticket['status'] == "Open":
                if st.button("Mark as Resolved", use_container_width=True):
                    update_ticket_status(selected_ticket_id, "Resolved")
                    send_update_ticket_status_email(selected_ticket, "Resolved")
                    st.rerun()
            else:
                if st.session_state.user_type == "instructor":
                    if st.button("Reopen Ticket", use_container_width=True):
                        update_ticket_status(selected_ticket_id, "Open")
                        send_update_ticket_status_email(selected_ticket, "Open")
                        st.rerun()

        st.divider()
        st.header("Profile")
        st.markdown(f"**{st.session_state.user}**   \n   *({st.session_state.email})*")
        st.radio("Avatar: ", ["Male", "Female"], horizontal=True, key="user_avatar")

        feedback_form = st.link_button("Feedback", url="https://forms.office.com/r/hVDQysi0B2",
                                       use_container_width=True)
        if st.button("Logout", use_container_width=True):
            logout()

    # Display selected ticket
    if selected_ticket_id:

        # Display ticket title and status
        st.subheader(f"{selected_ticket['title']}", divider="gray")
        st.markdown(f"**Ticket ID**: {selected_ticket_id}")
        if selected_ticket['status'] == "Open":
            st.markdown(f"**Status**: :green[{selected_ticket['status']}]")
        else:
            st.markdown(f"**Status**: {selected_ticket['status']}")

        # Display conversation history
        with st.expander("View Conversation History"):
            conv_messages = get_conv_messages(selected_ticket)
            for message in conv_messages:
                col1, col2 = st.columns([1, 12])
                col1.markdown(f"**{message['role']}**")
                col2.markdown(message['content'])

        # Display all chat messages for a ticket
        display_ticket_messages(selected_ticket)

        # Chat input and send message
        if selected_ticket['status'] == "Open":
            # Only allow new messages if ticket is open
            new_message = st.chat_input("Type your message here...")
        else:
            new_message = st.chat_input("Ticket is resolved. Reopen ticket to send new message.", disabled=True)
        if new_message:
            # Update ticket with new message for MongoDB
            try:
                add_message(selected_ticket_id, st.session_state.user, st.session_state.email, new_message)
            except Exception as e:
                st.error(f"Error sending message: {e}")

            # Send email
            if st.session_state.user_type == "instructor":
                recipient_name = selected_ticket['student_name']
                recipient_email = selected_ticket['student_email']
            else:
                recipient_name = selected_ticket['instructor_name']
                recipient_email = selected_ticket['instructor_email']
            recipient_email = "C210101@e.ntu.edu.sg"
            send_new_msg_email(selected_ticket, recipient_email, recipient_name, new_message)

            st.rerun()
