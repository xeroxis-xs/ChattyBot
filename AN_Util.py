
import os
from dotenv import load_dotenv
os.environ["AZURESEARCH_FIELDS_CONTENT"] = "chunk"              ## For Azure AI Search mapping, MUST BE DEFINED BEFORE IMPORT
os.environ["AZURESEARCH_FIELDS_CONTENT_VECTOR"] = "vector"      ## For Azure AI Search mapping, MUST BE DEFINED BEFORE IMPORT
from langchain_community.vectorstores.azuresearch import AzureSearch
from langchain_openai import AzureOpenAIEmbeddings
from langchain.callbacks import get_openai_callback


from pymongo import MongoClient                                 ## For MongoDB Connection
from bson.objectid import ObjectId


load_dotenv()
# print("ep: ", os.environ['CA_AZURE_VECTORSTORE_ENDPOINT'])
# print("key: ", os.environ['CA_AZURE_VECTORSTORE_KEY'])
# print("index: ", os.environ['CA_AZURE_VECTORSTORE_INDEX'])

class AN_Retriver:
    def __init__(self, model = "text-embedding-ada-002"):
        self.model = model
        ## Vector Score / Azure AI Search
        self.vector_store_endpoint = os.environ['CA_AZURE_VECTORSTORE_ENDPOINT']
        self.vector_store_key  = os.environ['CA_AZURE_VECTORSTORE_KEY']
        self.index_name = os.environ['CA_AZURE_VECTORSTORE_INDEX']  

        self.embeddings = AzureOpenAIEmbeddings(
            azure_deployment="asknarelle-experimental-text-embedding-ada-002"
        )

        self.vector_store= AzureSearch(
            azure_search_endpoint=self.vector_store_endpoint,
            azure_search_key=self.vector_store_key,
            index_name=self.index_name,
            embedding_function=self.embeddings.embed_query,
        )

    def get_vectorstore(self):
        return self.vector_store

    def search(self, query=None, search_type="similarity", k=3):
        vs = self.get_vectorstore()
        return vs.similarity_search(query=query, k=k, search_type=search_type)




class DBConnector:
    def __init__(self, DB_HOST, DB_USER=None, DB_PASS=None, DB_CONN_STRING=None):
        ## Local MONGO DB
        if DB_USER is not None:
            self.connection = MongoClient(DB_HOST, username=DB_USER, password=DB_PASS)
        else:
        ## AZURE CosmosDB RU
            self.connection = MongoClient(DB_HOST)
    
    def getDB(self, db):
        return self.connection[db]
    
    def getDocument(self, collection, id):
        return collection.find_one(ObjectId(id))
    
    


# from Narelle import Narelle
# from langchain.schema import HumanMessage, AIMessage, SystemMessage

def test():
    print("Starting Local Test...")

    queries = [
        "What is this course all about?",
        "who are the main instructor?",
        "what are the main assessment components?",
        "can I skip any of the classes?",
        "Can you list down the deadline for each assessments?",
        "How many classes do we need to attend each week?"
        "Can I apply leave of absent and skip the classes?",
    ]

    bot = Narelle()
    retrieve = AN_Retriver()

    # query = ""
    totalcost = 0
    query = input("Query: ")

    while query != "quit":
    # for query in queries:
        contexts = []

        documents = retrieve.search(query)
        for doc in documents:
            contexts.append(SystemMessage(content=f"context: {doc.page_content}"))


        with get_openai_callback() as cb:
            print(bot.answer_this(query=query, contexts=contexts))
            print(cb)
            if cb.total_tokens > 7500:
                bot.fade_memory()

            totalcost += cb.total_cost
        query = input("Next Query: ")

    for message in bot.messages:
        print(f"\n\n{message.type:6} : \n{message.content}")
    print(f"The total cost of this conversation is: {totalcost:.6f}")



if __name__ == "__main__":
    # test()
    print("[CA-SYS] AN_Retriver initialized")



