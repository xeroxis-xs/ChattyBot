import os
import time
from uuid import uuid4
from datetime import datetime
import pytz
from dotenv import load_dotenv

import streamlit as st
from streamlit_feedback import streamlit_feedback
from msal import ConfidentialClientApplication

from Narelle import Narelle
from AN_Util import DBConnector
import LongText
from Util import setup_logger


# Utility Functions
def get_time():
    curr_time = {
        "text": datetime.now(st.session_state.tz).strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp": datetime.now(st.session_state.tz).timestamp()
    }
    return curr_time


def update_feedback(response):
    st.session_state.display_messages[-1]['feedback'] = response
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
    del st.session_state.user
    del st.session_state.email
    del st.session_state.access_token
    st.session_state.conversation = []
    st.session_state.display_messages = None
    st.rerun()


def unauthorise(progress_text, error_msg):
    del st.session_state.user
    del st.session_state.email
    del st.session_state.accounts
    progress_bar.progress(100, text=progress_text)

    st.error(error_msg)
    st.button("Retry")

    time.sleep(2)
    progress_bar.empty()


@st.cache_data
def get_user_profile():
    return None


# @st.cache(allow_output_mutation=True)
# def get_user_auth():
#     APP_REGISTRATION_AUTHORITY = os.environ['APP_REG_AUTHORITY']
#     app = ConfidentialClientApplication(
#         client_id=os.environ['APP_REG_CLIENT_ID'],
#         authority=os.environ['APP_REG_AUTHORITY'],
#         client_credential=os.environ['APP_REG_CLIENT_SECRET']
#     )
#     result = None
#     st.session_state.accounts = app.get_accounts()
#     if not result:
#         result = app.acquire_token_interactive(scopes=["User.Read"])
#         st.session_state.accounts = app.get_accounts()
#     return result

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
    client_credential=CLIENT_SECRET
)

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
    print("No user in session state")
    st.session_state.user = None
if "email" not in st.session_state:
    st.session_state.email = None
if "access_token" not in st.session_state:
    st.session_state.access_token = None


# User has not signed in
if st.session_state.user is None:
    print("No user in session state")
    with informed_consent_form.container():
        # Display consent form
        with st.container(height=300):
            st.markdown(LongText.TERMS_OF_USE)
        # st.text_area("INFORMED CONSENT", label_visibility="collapsed" ,placeholder=LongText.TERMS_OF_USE, disabled=True, height=300)
        st.checkbox(LongText.CONSENT_ACKNOWLEDGEMENT, key="agreecheck")
        cols = st.columns(4)

        # Display buttons
        with cols[0]:
            btn_agree = st.button("Agree and Proceed", disabled=not st.session_state.agreecheck)
        with cols[1]:
            btn_inform_consent = st.link_button("Download Consent", url=os.environ['INFORM_CONSENT_SC1015'])

    # If user agrees to the terms of use
    if btn_agree:
        informed_consent_form.empty()
        auth_url = get_auth_url(app)
        st.markdown(
            f"To prevent unauthorised usage and abuse of the system, we will need you to verify that you are an NTU "
            f"student. Please follow the verification process below to continue...")
        # st.page_link(auth_url, label="Proceed to Verification")
        st.markdown(f'<a href="{auth_url}" target="_self">Proceed to Verification</a>', unsafe_allow_html=True)
        progress_bar = st.progress(0, text="Waiting...")

        # APP_REGISTRATION_CLIENT_ID = os.environ['APP_REG_CLIENT_ID']
        # app = PublicClientApplication(
        #     client_id=APP_REGISTRATION_CLIENT_ID,
        #     authority='https://login.microsoftonline.com/common'
        #     # token_cache=...  # Default cache is in memory only.
        #     # You can learn how to use SerializableTokenCache from
        #     # https://msal-python.readthedocs.io/en/latest/#msal.SerializableTokenCache
        # )
        # result = None
        #
        # # Firstly, check the cache to see if this end user has signed in before
        # st.session_state.accounts = app.get_accounts()

        # if accounts:
        #     logging.info("Account(s) exists in cache, probably with token too. Let's try.")
        #     print("Account(s) already signed in:")
        #     for a in accounts:
        #         print(a["username"])
        #     chosen = accounts[0]  # Assuming the end user chose this one to proceed
        #     print("Proceed with account: %s" % chosen["username"])
        #     # Now let's try to find a token in cache for this account
        #     result = app.acquire_token_silent(["User.Read"], account=chosen)

        # result = get_token_from_code(app)
        # progress_bar.progress(20, text="Authenticating...")

        # if not result:
        #     progress_bar.progress(20, text="Authenticating...")
        #
        #     # Option 1: Using Authentication Flow Instead:
        #     flow = app.initiate_device_flow(scopes=["User.Read"])
        #     st.write(
        #         f"\n1) Copy the Access Code: :red[{flow['user_code']}] \n2) Go to : {flow['verification_uri']}\n 3) Verify Identity with NTU Email\n 4) Accept App Access Permission.")
        #     result = app.acquire_token_by_device_flow(flow)
        #
        #     # Option 2: Using Popup Login (did not work with Azure Web App service):
        #     # result = app.acquire_token_interactive(scopes=["User.Read"])
        #
        #     progress_bar.progress(30, text="Receiving signals from microsoft server...")
        #     st.session_state.accounts = app.get_accounts()

        # Check for the authorization code in the query parameters
        auth_code = st.query_params.get("code")
        # auth_code = query_params.code
        logger.info(auth_code)

        if auth_code:
            result = get_token_from_code(app, auth_code)
            logger.info(result)
            # If login is successful
            if "access_token" in result:
                progress_bar.progress(50, text="Retrieving & checking profile")

                st.session_state.user = result['id_token_claims']['name']
                st.session_state.email = result['id_token_claims']['preferred_username']

                logger.info(st.session_state.user)

                st.session_state.mongodb = DBConnector(DB_HOST).getDB(DB_NAME)
                allowed_users = st.session_state.mongodb.users_permission.find_one({"status": "allowed"})['users']
                blocked_users = st.session_state.mongodb.users_permission.find_one({"status": "blocked"})['users']

                if st.session_state.email in blocked_users:
                    unauthorise(progress_text="Unauthorised user...", error_msg="This account has been blocked")

                elif "ntu.edu.sg" in st.session_state.email[-10:] or st.session_state.email in allowed_users:
                    LLM_DEPLOYMENT_NAME = os.environ['AZURE_OPENAI_DEPLOYMENT_NAME']
                    LLM_MODEL_NAME = os.environ['AZURE_OPENAI_MODEL_NAME']
                    st.session_state.llm = Narelle(deployment_name=LLM_DEPLOYMENT_NAME, model_name=LLM_MODEL_NAME)

                    # Initializing Conversations
                    progress_bar.progress(70, text="Waking up Narelle...")
                    st.session_state.starttime = get_time()
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

                    st.session_state.conv_id = st.session_state.mongodb.conversations.insert_one(
                        conversation).inserted_id

                    st.session_state.conversation = []
                    st.session_state.display_messages = [
                        {"role": "ai", "content": f"{LongText.NARELLE_GREETINGS}", "recorded_on": get_time()}]

                    progress_bar.progress(100, text="Narelle is Ready")
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
    # Create a new feedback key if not exist
    if "fb_key" not in st.session_state:
        st.session_state.fb_key = str(uuid4())

    # Display all chat messages
    for message in st.session_state.display_messages:
        role = message["role"]

        # AI message
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
                # if message == st.session_state.display_messages[-1]:

        # User message
        else:
            with st.chat_message(role, avatar=chat_avatars[role][st.session_state.user_avatar]):
                # Display message content
                st.markdown(message["content"])

    ## INPUT QUESTION AND PROCESS QUERY
    if question := st.chat_input("Type in your question here"):
        st.chat_message("user", avatar=chat_avatars['user'][st.session_state.user_avatar]).markdown(question)
        u_message = {"role": "user", "content": question, "recorded_on": get_time()}
        st.session_state.display_messages.append(u_message)
        st.session_state.conversation.append(u_message)
        st.session_state.mongodb.conversations.update_one({"_id": st.session_state.conv_id},
                                                          {"$push": {"messages": u_message},
                                                           "$set": {"last_interact": get_time()}})
        if "thank" in question:
            st.balloons()

        answer, token_cost, sources = st.session_state.llm.answer_this(query=question)
        sources_text = ""
        if "sorry" not in answer:
            sources_text = f"\n\n\n **Sources:** *{sources}*"
        answer = f"{answer} {sources_text}"

        with st.chat_message("ai", avatar=chat_avatars['ai']):
            st.markdown(answer)
            ## If recent responds got feedback

        ai_message = {"role": "ai", "content": f"{answer}", "recorded_on": get_time(), "token_cost": token_cost}
        st.session_state.display_messages.append(ai_message)
        st.session_state.conversation.append(ai_message)
        st.session_state.mongodb.conversations.update_one({"_id": st.session_state.conv_id},
                                                          {"$push": {"messages": ai_message},
                                                           "$set": {"last_interact": get_time(),
                                                                    "overall_cost": st.session_state.llm.get_total_tokens_cost()}})

    if len(st.session_state.display_messages) > 1:
        streamlit_feedback(
            feedback_type="thumbs",
            optional_text_label="[Optional] let us know what do you think about this response...",
            key=st.session_state.fb_key,
            on_submit=update_feedback
        )

    with st.sidebar:
        st.header("Profile")
        st.markdown(f"**{st.session_state.user}**   \n   *({st.session_state.email})*")
        st.radio("Avatar: ", ["Male", "Female"], horizontal=True, key="user_avatar")
        if "Ong Chin Ann" in st.session_state.user:
            costing = st.session_state.llm.get_total_tokens_cost()
            st.metric("Consumption for this conversation", f"USD {costing['overall_cost']:.4f}",
                      delta=f"Tokens: {costing['overall_tokens']}", delta_color="off")
            st.markdown(
                f"<span style='font-size:8pt; '>Azure OpenAI Service Version: {os.environ['OPENAI_API_VERSION']}</span>",
                unsafe_allow_html=True)

        feedback_form = st.link_button("Feedback", url="https://forms.office.com/r/hVDQysi0B2",
                                       use_container_width=True)
        if st.button("Logout", use_container_width=True):
            logout()
