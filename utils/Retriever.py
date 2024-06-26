import os
from langchain_community.callbacks import get_openai_callback
os.environ["AZURESEARCH_FIELDS_CONTENT"] = "chunk"              ## For Azure AI Search mapping, MUST BE DEFINED BEFORE IMPORT
os.environ["AZURESEARCH_FIELDS_CONTENT_VECTOR"] = "vector"      ## For Azure AI Search mapping, MUST BE DEFINED BEFORE IMPORT
from langchain_community.vectorstores.azuresearch import AzureSearch
from langchain_openai import AzureOpenAIEmbeddings


class Retriever:
    def __init__(self, model = "text-embedding-ada-002"):
        self.model = model
        # Vector Score / Azure AI Search
        self.vector_store_endpoint = os.environ['CA_AZURE_VECTORSTORE_ENDPOINT']
        self.vector_store_key = os.environ['CA_AZURE_VECTORSTORE_KEY']
        self.index_name = os.environ['CA_AZURE_VECTORSTORE_INDEX']  
        
        # print(f"TEXT EMBEDDING: {os.environ['CA_AZURE_TEXT_EMBEDDING']}")
        self.embeddings = AzureOpenAIEmbeddings(
            azure_deployment=os.environ['CA_AZURE_TEXT_EMBEDDING']
        )

        self.vector_store = AzureSearch(
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


def test_single_input():

    bot = Narelle(
        deployment_name=os.environ['AZURE_OPENAI_DEPLOYMENT_NAME'],
        model_name=os.environ['AZURE_OPENAI_MODEL_NAME'],
        temperature=0
    )
    total_cost = 0
    query = input("Query: ")

    with get_openai_callback() as cb:
        print(bot.answer_this(query=query))
        print(cb)
        if cb.total_tokens > 7500:
            bot.fade_memory()

        total_cost += cb.total_cost

    for message in bot.messages:
        print(f"\n\n{message.type:6} : \n{message.content}")
    print(f"The total cost of this conversation is: {total_cost:.6f}")


def test_multiple_preset_input():

    queries = [
        # "What is this course all about?",
        "who are the main instructor?",
        # "what are the main assessment components?",
        # "can I skip any of the classes?",
        # "Can you list down the deadline for each assessment?",
        # "How many classes do we need to attend each week?"
        # "Can I apply leave of absent and skip the classes?",
    ]

    bot = Narelle(
        deployment_name=os.environ['AZURE_OPENAI_DEPLOYMENT_NAME'],
        model_name=os.environ['AZURE_OPENAI_MODEL_NAME'],
        temperature=0
    )

    total_cost = 0
    for query in queries:

        with get_openai_callback() as cb:
            print(bot.answer_this(query=query))
            print(cb)
            if cb.total_tokens > 7500:
                bot.fade_memory()
            total_cost += cb.total_cost

    for message in bot.messages:
        print(f"\n\n{message.type:6} : \n{message.content}")
    print(f"The total cost of this conversation is: {total_cost:.6f}")


if __name__ == "__main__":
    from dotenv import load_dotenv
    from Narelle import Narelle
    load_dotenv()

    print("[CA-SYS] Retriever initialized")
    test_single_input()
