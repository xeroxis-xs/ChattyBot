import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.memory import ConversationBufferMemory
from langchain.callbacks import get_openai_callback

from AN_Util import AN_Retriver

from datetime import datetime
import pytz


load_dotenv()

class Narelle:
    def __init__(self, 
                deployment_name='asknarelle-experimental-gpt-35-turbo',
                model_name="gpt-3.5-turbo-instruct",
                temperature=0):
        tz = pytz.timezone("Asia/Singapore")
        now = datetime.now(tz).strftime("%Y-%m-%d")
        self.llm = AzureChatOpenAI(deployment_name=deployment_name, 
                                   model_name=model_name, 
                                #    azure_endpoint=os.environ['AZURE_OPENAI_ENDPOINT'],
                                #    api_key=os.environ['OPENAI_API_KEY'],
                                   temperature=temperature)
        self.retriever = AN_Retriver()
        self.memory = ConversationBufferMemory()

        sysmsg = f"You are a university course assistant. Your name is Narelle. Your task is to answer student queries for the course {os.environ['COURSE_NAME']} based on the information retrieved from the knowledge base (as of {os.environ['LAST_CONTENT_UPDATE']}) along with the conversation with user. There are some terminologies which referring to the same thing, for example: assignment is also refer to assessment, project also refer to mini-project, test also refer to quiz. Week 1 starting from 15 Jan 2024, Week 8 starting from 11 March 2024, while Week 14 starting from 22 April 2024. \n\nIn addition to that, the second half of this course which is the AI part covers the syllabus and content from the textbook named 'Artificial Intelligence: A Modern Approach (3rd edition)' by Russell and Norvig . When user ask for tips or sample questions for AI Quiz or AI Theory Quiz, you can generate a few MCQ questions with the answer based on the textbook, 'Artificial Intelligence: A Modern Approach (3rd edition)' from Chapter 1, 2, 3, 4, and 6. Lastly, remember today is {now} in the format of YYYY-MM-DD.\n\nIf you are unsure how to respond to a query based on the course information provided, just say sorry, inform the user you are not sure, and recommend the user to email to the course coordinator or instructors (smitha@ntu.edu.sg | chinann.ong@ntu.edu.sg)."

        self.instruction = SystemMessage(content=sysmsg)            
        self.messages = [self.instruction]

        self.total_api_cost = 0
        self.total_api_tokens = 0


        
    def get_llm(self):
        return self.llm
    
    def get_context(self, query, k=5):
        contexts = []
        sources = []

        documents = self.retriever.search(query, k=k)
        for doc in documents:
            contexts.append(SystemMessage(content=f"context: {doc.page_content}"))
            sources.append(doc.metadata['title'].split(".")[0])
        # print(f"LIST: {sources}\nSET: {set(sources)}")
        return contexts, list(set(sources))
    
    def get_total_tokens_cost(self):
        return {"overall_cost": self.total_api_cost, "overall_tokens":self.total_api_tokens}

    def answer_this(self, query, contexts=None):

        # Copying previous conversations for this local context
        localcontext = self.messages.copy()

        # If no context provided, then retrieve document / context based on the query
        if contexts is None:
            contexts, sources = self.get_context(query)

        # Construct user query into User Message and append to local context and conversation later
        humanquery = HumanMessage(content=query)

        if contexts is not None:
            localcontext.extend(contexts)
            localcontext.append(humanquery)
            
            with get_openai_callback() as cb:
                response = self.llm.invoke(localcontext)
                self.total_api_cost += cb.total_cost
                self.total_api_tokens += cb.total_tokens
                cost = {"cost": f"{cb.total_cost:.8f}", "tokens":cb.total_tokens}

                # Check if current token almost exceeded limit, then try to fade the previous memory
                print(f"tokens: {cb.total_tokens}")
                if cb.total_tokens > 8000:
                    self.fade_memory()

            self.messages.extend([humanquery, response])

        else:
            response = SystemMessage(content="No context provided, hence no response")
        return response.content, cost, sources
    

    # def answer_this(self, query, contexts=None):

    #     return self.get_response(query, contexts=contexts)


    def fade_memory(self):
        self.messages.pop(1)

def test():
    print("Starting Local Test...")
    bot = Narelle()
    query = input("Query : ")
    while query != "quit":

        answer = bot.answer_this(query=query)
        print(f"AI   :{answer}")
        query = input("Query : ")

    for message in bot.messages:
        print(f"\n\n{message.type:6} : \n{message.content}")
    print(f"The total cost of this conversation is: {bot.total_api_cost:.6f}")

if __name__ == "__main__":
    print("[CA-SYS] Start")
    # test()
    print("[CA-SYS] Agent initialized")