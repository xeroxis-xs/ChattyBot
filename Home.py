import random
import time
from datetime import datetime
import pytz
import os
import requests
from dotenv import load_dotenv

import streamlit as st
from msal import ConfidentialClientApplication, PublicClientApplication

from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage, AIMessage, SystemMessage

import webbrowser

from Narelle import Narelle
from AN_Util import DBConnector
import LongText

def getTime():
    curr_time = {
                    "text" : datetime.now(st.session_state.tz).strftime("%Y-%m-%d %H:%M:%S"),
                    "timestamp": datetime.now(st.session_state.tz).timestamp()
                }
    return curr_time

def streaming_respond(msg):
    for word in msg.split(" "):
        yield word + " "
        time.sleep(0.05)

def logout():

    del st.session_state.user
    del st.session_state.email
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



################## MAIN ##############################
load_dotenv(override=True)

st.set_page_config(page_title='AskNarelle - Your friendly course assistant', page_icon="🙋‍♀️")
st.title(":woman-raising-hand: Ask Narelle")
st.write(f"For queries related to {os.environ['COURSE_NAME']}")
# st.markdown(LongText.PAGE_STYLE, unsafe_allow_html=True)


# APP SETUP
informed_consent_form = st.empty()
st.session_state.tz = pytz.timezone("Asia/Singapore")
chat_avatars = {"ai":"imgs/ai_avatar.jpg", 
                "user": {"Male":"imgs/male_user_avatar.jpg",
                         "Female":"imgs/female_user_avatar.jpg"}}


if "user" not in st.session_state:
    with informed_consent_form.container():
        with st.container(height=300):
            st.markdown(LongText.TERMS_OF_USE)
        # st.text_area("INFORMED CONSENT", label_visibility="collapsed" ,placeholder=LongText.TERMS_OF_USE, disabled=True, height=300)
        st.checkbox(LongText.CONSENT_ACKNOWLEDGEMENT, key="agreecheck")
        cols = st.columns(4)
        with cols[0]:
            btn_agree = st.button("Agree and Proceed", disabled=not(st.session_state.agreecheck))
        with cols[1]:
            btn_inform_consent = st.link_button("Download Consent", url=os.environ['INFORM_CONSENT_SC1015'])


    if btn_agree:
        informed_consent_form.empty()
        st.markdown(''':red[To prevent unauthorise usage and abuse of the system, we will need you to verify that you are an NTU student. Please follow the verfication process below to continue... ]''')
        progress_bar = st.progress(0, text="Preparing...")
        
        APP_REGISTRATION_CLIENT_ID = os.environ['APP_REG_CLIENT_ID']
        app = PublicClientApplication(
        client_id=APP_REGISTRATION_CLIENT_ID, 
        authority='https://login.microsoftonline.com/common'
        # token_cache=...  # Default cache is in memory only.
                        # You can learn how to use SerializableTokenCache from
                        # https://msal-python.readthedocs.io/en/latest/#msal.SerializableTokenCache
        )
        result = None

        # Firstly, check the cache to see if this end user has signed in before
        st.session_state.accounts = app.get_accounts()
        # if accounts:
        #     logging.info("Account(s) exists in cache, probably with token too. Let's try.")
        #     print("Account(s) already signed in:")
        #     for a in accounts:
        #         print(a["username"])
        #     chosen = accounts[0]  # Assuming the end user chose this one to proceed
        #     print("Proceed with account: %s" % chosen["username"])
        #     # Now let's try to find a token in cache for this account
        #     result = app.acquire_token_silent(["User.Read"], account=chosen)

        if not result:
            progress_bar.progress(20, text="Authenticating...")

            
            # Option 1: Using Authentication Flow Instead:
            # flow = app.initiate_device_flow(scopes=["User.Read"])
            # st.write(f"\n1) Copy the Access Code: :red[{flow['user_code']}] \n2) Go to : {flow['verification_uri']}\n 3) Verify Identity with NTU Email\n 4) Accept App Access Permission.")
            # result = app.acquire_token_by_device_flow(flow)

            
            # Option 2: Using Popup Login:
            result = app.acquire_token_interactive(scopes=["User.Read"])
            
            progress_bar.progress(30, text="Receiving signals from microsoft server...")
            st.session_state.accounts = app.get_accounts()
                
        
        if "access_token" in result:
            progress_bar.progress(50, text="Retriving & checking profile")
            st.session_state.user = result['id_token_claims']['name']
            st.session_state.email = result['id_token_claims']['preferred_username']

            LLM_DEPLOYMENT_NAME = os.environ['AZURE_OPENAI_DEPLOYMENT_NAME']
            LLM_MODEL_NAME = os.environ['AZURE_OPENAI_MODEL_NAME']
            st.session_state.llm = Narelle(deployment_name=LLM_DEPLOYMENT_NAME, model_name=LLM_MODEL_NAME)

            DB_HOST = os.environ['CA_MONGO_DB_HOST']
            DB_USER = os.environ['CA_MONGO_DB_USER']
            DB_PASS = os.environ['CA_MONGO_DB_PASS']
            DB_NAME = os.environ['CA_MONGO_DB']
            st.session_state.mongodb = DBConnector(DB_HOST).getDB(DB_NAME)
            allowed_users = st.session_state.mongodb.users_permission.find_one({"status":"allowed"})['users']
            blocked_users = st.session_state.mongodb.users_permission.find_one({"status":"blocked"})['users']
            
            if st.session_state.email in blocked_users:
                unauthorise(progress_text="Unauthorised user...", error_msg="This account has been blocked")

            elif "ntu.edu.sg" in st.session_state.email[-10:] or st.session_state.email in allowed_users:
                ## Initializing Conversations
                progress_bar.progress(70, text="Waking up Narelle...")
                st.session_state.starttime = getTime()
                conversation = {
                    "stime" : getTime(),
                    "user": st.session_state.user,
                    "email": st.session_state.email,
                    "messages":[],
                    "last_interact": getTime(),
                    "llm_deployment_name":os.environ['AZURE_OPENAI_DEPLOYMENT_NAME'],
                    "llm_model_name": os.environ['AZURE_OPENAI_MODEL_NAME'],
                    "vectorstore_index":os.environ['CA_AZURE_VECTORSTORE_INDEX']
                }
                st.session_state.conv_id = st.session_state.mongodb.conversations.insert_one(conversation).inserted_id

                st.session_state.conversation = []
                st.session_state.display_messages = [{"role":"ai", "content":f"{LongText.NARELLE_GREETINGS}", "recorded_on": getTime()}]

                progress_bar.progress(100, text="Narelle is Ready")
                time.sleep(1)
                progress_bar.empty()
                st.rerun()
            
            else:
                unauthorise(progress_text="Unauthorised user...", error_msg="Please verify using your NTU email address")

                
        else:
            st.write(result.get("error"))
            st.write(result.get("error_description"))
            st.write(result.get("correlation_id"))  # You may need this when reporting a bug

else:
    for message in st.session_state.display_messages:
        role = message["role"]
        if role == 'ai':
            with st.chat_message(role, avatar=chat_avatars[role]):
                st.markdown(message["content"])
        else:
            with st.chat_message(role, avatar=chat_avatars[role][st.session_state.user_avatar]):
                st.markdown(message["content"])

    if question:= st.chat_input("Type in your question here"):
        st.chat_message("user", avatar=chat_avatars['user'][st.session_state.user_avatar]).markdown(question)
        u_message = {"role":"user", "content":question, "recorded_on": getTime()}
        st.session_state.display_messages.append(u_message)
        st.session_state.conversation.append(u_message)
        st.session_state.mongodb.conversations.update_one({"_id":st.session_state.conv_id}, {"$push":{"messages":u_message}, "$set":{"last_interact": getTime()}})
        if "thank" in question:
            st.balloons()
        
        
        answer, token_cost = st.session_state.llm.answer_this(query=question)
        st.chat_message("ai", avatar=chat_avatars['ai']).markdown(answer)
        # with st.chat_message("assistant"):
        #     st.write_stream(streaming_respond(answer))
        

        ai_message = {"role":"ai", "content":f"{answer}", "recorded_on": getTime(), "token_cost":token_cost}
        st.session_state.display_messages.append(ai_message)
        st.session_state.conversation.append(ai_message)
        st.session_state.mongodb.conversations.update_one({"_id":st.session_state.conv_id}, {"$push":{"messages":ai_message}, "$set":{"last_interact": getTime(), "overall_cost":st.session_state.llm.get_total_tokens_cost()}})
    
    with st.sidebar:
        st.header("Profile")
        st.markdown(f"**{st.session_state.user}**   \n   *({st.session_state.email})*")
        st.radio("Avatar: ", ["Male", "Female"], horizontal=True, key="user_avatar")
        costing = st.session_state.llm.get_total_tokens_cost()
        st.metric("Consumption for this conversation", f"USD {costing['overall_cost']:.4f}", delta=f"Tokens: {costing['overall_tokens']}", delta_color="off")

        feedback_form = st.link_button("Feedback", url="https://forms.office.com/r/hVDQysi0B2", use_container_width=True)
        if st.button("Logout", use_container_width=True):
            logout()

