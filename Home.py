import os
import time
import asyncio
from io import BytesIO
import requests
from uuid import uuid4
from datetime import datetime
import pytz
import json
from dotenv import load_dotenv
from streamlit_feedback import streamlit_feedback
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


def update_feedback(response):
    st.session_state.all_messages[-1]['feedback'] = response
    st.session_state.fb_key = str(uuid4())
    msg_count = len(st.session_state.mongodb.conversations.find_one({"_id": st.session_state.conv_id})["messages"]) - 1
    # st.toast(f"Total Msg: {msg_count}")
    st.session_state.mongodb.conversations.update_one(
        {"_id": st.session_state.conv_id},
        {"$set": {f"messages.{msg_count}.feedback": response}}
    )
    st.toast("Thanks for your feedback")


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


def unauthorise(progress_bar, progress_text, error_msg):
    st.query_params.clear()
    del st.session_state.user
    del st.session_state.email
    del st.session_state.auth_code
    progress_bar.progress(100, text=progress_text)

    st.error(error_msg)
    st.button("Retry")

    time.sleep(2)
    progress_bar.empty()


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


def upload_user_message_to_db(content):
    u_message = {"role": "user", "content": content, "recorded_on": get_time()}
    # Append user message to all_messages state
    st.session_state.all_messages.append(u_message)
    st.session_state.mongodb.conversations.update_one(
        {"_id": st.session_state.conv_id},
        {"$push": {"messages": u_message},
         "$set": {"last_interact": get_time()}}
    )


def upload_ai_message_to_db(content, token_cost=None):
    ai_message = {"role": "ai", "content": f"{content}", "recorded_on": get_time(), "token_cost": token_cost}
    # Append ai message to all_messages state
    st.session_state.all_messages.append(ai_message)
    st.session_state.mongodb.conversations.update_one(
        {"_id": st.session_state.conv_id},
        {"$push": {"messages": ai_message},
         "$set": {"last_interact": get_time(),
                  "overall_cost": st.session_state.narelle.get_total_tokens_cost()}}
    )


def click_ticket_button(button):
    if button == "Yes":
        upload_user_message_to_db("Yes")
        st.session_state.creating_ticket = True
    else:
        upload_user_message_to_db("No")
    # Enable input field after AI has responded
    st.session_state.chat_input = True


def create_ticket(latest_query):
    # Initializing Ticket
    ticket_title = st.session_state.narelle.create_ticket_title(latest_query)
    ticket = {
        "student_name": st.session_state.user,
        "conversation_id": st.session_state.conv_id,
        "student_email": st.session_state.email,
        "instructor_name": os.environ['INSTRUCTOR_NAME'],
        "instructor_email": os.environ['INSTRUCTOR_EMAIL'],
        "title": ticket_title,
        "stime": get_time(),
        "status": "Open",
        "messages": []
    }

    # Insert the ticket into Mongo DB
    ticket_id = st.session_state.mongodb.tickets.insert_one(ticket).inserted_id
    return ticket_id, ticket_title


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


def send_new_ticket_email(email_client, ticket_id, ticket_title):
    try:
        # Read HTML template
        new_ticket_html_template = email_client.read_html_template("email_template/new_ticket_for_email_template.html")
        # Customize HTML content
        html_body = new_ticket_html_template.format(
            ticket_id=ticket_id,
            ticket_title=ticket_title,
            streamlit_app_url="https://asknarelle.azurewebsites.net/"
        )

        subject = f"[AskNarelle] New Ticket Created: {ticket_title}"
        plain_text_body = ticket_title
        from_email = "DoNotReply@140197c9-8f19-4c8a-9bb4-23adfc6600ef.azurecomm.net"
        # Send to both student and instructor
        message = email_client.draft_email(
            subject,
            html_body,
            plain_text_body,
            [st.session_state.email, os.environ['INSTRUCTOR_EMAIL']],
            [st.session_state.formatted_name, os.environ['INSTRUCTOR_NAME']],
            from_email
        )
        email_client.send_email(message)
    except Exception as e:
        st.error(f"Error sending email notification: {e}")

async def main():
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
    logger.info("----------- New state ----------")

    # Initialise App Registration
    app = ConfidentialClientApplication(
        client_id=CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET
    )

    # Initialise Email Client
    email_client = AzureEmailClient()

    # Initialise Streamlit App
    st.set_page_config(page_title='AskNarelle - Your friendly course assistant', page_icon="🙋‍♀️")
    st.title(":woman-raising-hand: Ask Narelle")
    st.write(f"For queries related to {os.environ['COURSE_NAME']}")

    informed_consent_form = st.empty()
    st.session_state.tz = pytz.timezone("Asia/Singapore")
    chat_avatars = {
        "ai": "imgs/ai_avatar.jpg",
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
    if 'chat_input' not in st.session_state:
        # Initialise chat_input as True
        st.session_state.chat_input = True
    if 'creating_ticket' not in st.session_state:
        st.session_state.creating_ticket = False
    if 'latest_query' not in st.session_state:
        st.session_state.latest_query = None

    # User has not signed in
    if st.session_state.user is None:
        st.session_state.auth_code = st.query_params.get("code")
        # Clear query parameters
        st.query_params.clear()
        if st.session_state.auth_code is None:
            logger.info("No auth code found, displaying consent form")
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

        # When user was redirected back from the authentication page with an auth code in url params
        else:
            logger.info("Auth code found, attempting to get token")
            progress_bar = st.progress(20, text="Authenticating...")
            result = get_token_from_code(app, st.session_state.auth_code)
            logger.info(f"access_token found in result")
            # If login is successful
            if "access_token" in result:
                logger.info("Token is valid and saved to local storage")
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
                    unauthorise(progress_bar, progress_text="Unauthorised user...", error_msg="This account has been blocked")

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
                    unauthorise(progress_bar,
                                progress_text="Unauthorised user...",
                                error_msg="Please verify using your NTU email address")

            # Login failed
            else:
                logger.error("Authentication failed")
                st.write(result.get("error"))
                st.write(result.get("error_description"))
                st.write(result.get("correlation_id"))  # You may need this when reporting a bug

    # User has signed in
    else:
        # Display sidebar
        with st.sidebar:
            st.header("Profile")
            st.markdown(f"**{st.session_state.user}**   \n   *({st.session_state.email})*")
            st.radio("Avatar: ", ["Male", "Female"], horizontal=True, key="user_avatar")
            if "Ong Chin Ann" in st.session_state.user:
                costing = st.session_state.narelle.get_total_tokens_cost()
                st.metric("Consumption for this conversation", f"USD {costing['overall_cost']:.4f}",
                          delta=f"Tokens: {costing['overall_tokens']}", delta_color="off")
                st.markdown(
                    f"<span style='font-size:8pt; '>Azure OpenAI Service Version: {os.environ['OPENAI_API_VERSION']}</span>",
                    unsafe_allow_html=True)

            feedback_form = st.link_button("Feedback", url="https://forms.office.com/r/hVDQysi0B2",
                                           use_container_width=True)
            if st.button("Logout", use_container_width=True):
                logout()
        # # Clear query parameters
        # st.query_params.clear()
        # Create a new feedback key if not exist
        if "fb_key" not in st.session_state:
            st.session_state.fb_key = str(uuid4())

        # Display all chat messages
        for message in st.session_state.all_messages:
            role = message["role"]

            # Display AI messages
            if role == 'ai':
                with st.chat_message(role, avatar=chat_avatars[role]):
                    # Display message content
                    st.markdown(message["content"])
                    # If user mark thumbs up or thumbs down
                    if "feedback" in message:
                        if message['feedback'] is not None:
                            # Display feedback, thumbs up or thumbs down
                            st.markdown(f"<div style='text-align:right;'>{message['feedback']['score']}</div>",
                                        unsafe_allow_html=True, )
                    # if message == st.session_state.all_messages[-1]:

            # Display User messages
            else:
                with st.chat_message(st.session_state.formatted_name, avatar=st.session_state.user_photo):
                    # Display message content
                    st.markdown(message["content"])

        # Display new ticket created message
        if st.session_state.creating_ticket:
            with st.chat_message("ai", avatar=chat_avatars['ai']):
                with st.spinner("Creating a ticket for you..."):
                    # Create a ticket
                    ticket_id, ticket_title = create_ticket(st.session_state.latest_query)
                new_ticket_message = (f"New Ticket has been created for you!\n\n"
                                      f"**Ticket ID:** {ticket_id}\n\n"
                                      f"**Ticket Title:** {ticket_title}\n\n"
                                      f"You will receive an email notification once the instructor has responded to your "
                                      f"query. The email will be flagged as **junk**, so please check your junk mail "
                                      f"folder for updates.\n\nAlternatively, you can check or update the status of your "
                                      f"ticket by navigating to **Ticket**.")
                st.markdown(new_ticket_message)
                upload_ai_message_to_db(new_ticket_message)

            st.session_state.creating_ticket = False
            send_new_ticket_email(email_client, ticket_id, ticket_title)


        # Display feedback form if the latest message is from AI
        if st.session_state.all_messages[-1]["role"] == "ai":
            streamlit_feedback(
                feedback_type="thumbs",
                optional_text_label="[Optional] let us know what do you think about this response...",
                key=st.session_state.fb_key,
                on_submit=update_feedback
            )

        # Input field for user to type in query and process query
        if query := (st.chat_input("Type in your query here", disabled=not st.session_state.chat_input)
                     or not st.session_state.chat_input):
            # If chat input is enabled
            if st.session_state.chat_input:
                # Display user message
                with st.chat_message(st.session_state.formatted_name, avatar=st.session_state.user_photo):
                    # Set latest user query
                    st.session_state.latest_query = query
                    st.markdown(query)

                if "thank" in query:
                    st.balloons()
                upload_user_message_to_db(query)
                # Disable input field until AI has responded
                st.session_state.chat_input = False
                st.rerun()

            # Display AI message
            with st.chat_message("ai", avatar=chat_avatars['ai']):
                with st.spinner('Narelle is processing your query...'):
                    # Run both LLM calls concurrently and wait for their results
                    (answer, token_cost, sources), is_trivial = await asyncio.gather(
                        st.session_state.narelle.answer_this(query=st.session_state.latest_query),
                        st.session_state.narelle.is_trivial_query(st.session_state.latest_query)
                    )

                    # # Get response from Narelle
                    # answer, token_cost, sources = st.session_state.narelle.answer_this(st.session_state.latest_query)
                    # # Check if the query is trivial
                    # is_trivial = st.session_state.narelle.is_trivial_query(st.session_state.latest_query)

                # with st.spinner('Evaluating response...'):
                #     # Evaluate the response
                #     raw_answer = raw_s = r'{}'.format(answer)
                #     prompt_ticket = st.session_state.narelle.evaluate(response=raw_answer)
                #     logger.info(f"Require Prompt Ticket? {prompt_ticket}")
                # Append sources to the answer
                sources_text = f"\n\n\n **Sources:** *{sources}*"
                if not is_trivial:
                    # Non-Trivial, require ticket, Remove sources_text
                    sources_text = ""
                answer = f"{answer} {sources_text}"
                # Display AI response
                st.markdown(answer)
                upload_ai_message_to_db(answer, token_cost)

                # Enable input field after AI has responded
                st.session_state.chat_input = True
                if is_trivial:
                    # Does not require ticket
                    st.rerun()

            # Prompt user to raise a ticket if AI response is unable to answer query
            if not is_trivial:
                # Require Ticket
                # Display AI message
                with st.chat_message("ai", avatar=chat_avatars['ai']):
                    prompt_ticket_message = ("It seems like you require further assistance. Would you like to raise a "
                                             "ticket to reach out to the course instructor?")
                    st.markdown(prompt_ticket_message)
                    upload_ai_message_to_db(prompt_ticket_message)
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        logger.info(f"Render button")
                        st.button("Yes", type="primary", use_container_width=True, on_click=click_ticket_button,
                                  args=['Yes'])
                    with col2:
                        st.button("No", type="secondary", use_container_width=True, on_click=click_ticket_button,
                                  args=['No'])



if __name__ == '__main__':
    asyncio.run(main())


