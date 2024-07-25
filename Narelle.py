import os
import pytz
import asyncio
from datetime import datetime
from langchain_openai import AzureChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain_community.callbacks import get_openai_callback
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field

from utils.Retriever import Retriever


class Result(BaseModel):
    classification: str = Field(
        description="The classification of the response, either SUGGESTED TO REACH OUT or NOT SUGGESTED TO REACH OUT"
    )
    reason: str = Field(description="The reason for the classification")


class Narelle:
    def __init__(self, deployment_name, model_name, temperature=0):
        tz = pytz.timezone("Asia/Singapore")
        now = datetime.now(tz).strftime("%Y-%m-%d")
        self.llm = AzureChatOpenAI(
            deployment_name=deployment_name,
            model_name=model_name,
            temperature=temperature
        )
        # self.llm_with_eval = DeepEvalAzureOpenAI(model=self.llm)
        # deepeval.login_with_confident_api_key("your-confident-api-key")
        #
        # self.metric = FaithfulnessMetric(
        #     threshold=0.3,
        #     model=self.llm_with_eval,
        #     include_reason=True
        # )

        self.retriever = Retriever()
        self.memory = ConversationBufferMemory()
        self.parser = JsonOutputParser(pydantic_object=Result)

        sys_msg = (f"You are a university course assistant. Your name is Narelle. Your task is to answer student "
                   f"queries for the course {os.environ['COURSE_NAME']} based on the information retrieved from the "
                   f"knowledge base (as of {os.environ['LAST_CONTENT_UPDATE']}) along with the conversation with user. "
                   f"There are some terminologies which referring to the same thing, for example: assignment is also "
                   f"refer to assessment, project also refer to mini-project, test also refer to quiz. Week 1 starting "
                   f"from 15 Jan 2024, Week 8 starting from 11 March 2024, while Week 14 starting from 22 April 2024. "
                   f"\n\nIn addition to that, the second half of this course which is the AI part covers the syllabus "
                   f"and content from the textbook named 'Artificial Intelligence: A Modern Approach (3rd edition)' by "
                   f"Russell and Norvig . When user ask for tips or sample questions for AI Quiz or AI Theory Quiz, "
                   f"you can generate a few MCQ questions with the answer based on the textbook, 'Artificial "
                   f"Intelligence: A Modern Approach (3rd edition)' from Chapter 1, 2, 3, 4, and 6. Lastly, "
                   f"remember today is {now} in the format of YYYY-MM-DD.\n\n If the user asks you a question you "
                   f"don't know the answer to, just apologise and inform the user you are not sure, "
                   f"and recommend the user to email to the course coordinator or instructors (smitha@ntu.edu.sg | "
                   f"chinann.ong@ntu.edu.sg).")

        self.instruction = SystemMessage(content=sys_msg)
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
        return {"overall_cost": self.total_api_cost, "overall_tokens": self.total_api_tokens}

    async def answer_this(self, query, contexts=None):
        sources = []

        # Copying previous conversations for this local context
        local_context = self.messages.copy()

        # If no context provided, then retrieve document / context based on the query
        if contexts is None:
            contexts, sources = self.get_context(query)

        # Construct user query into User Message and append to local context and conversation later
        human_query = HumanMessage(content=query)

        if contexts is not None:
            local_context.extend(contexts)
            local_context.append(human_query)

            with get_openai_callback() as cb:
                response = self.llm.ainvoke(local_context)
                # print(response)
                # test_case = LLMTestCase(
                #     input=query,
                #     actual_output=response.content,
                #     retrieval_context=[context.content for context in contexts]
                # )
                # self.metric.measure(test_case)
                # print(self.metric.score)
                # print(self.metric.reason)
                self.total_api_cost += cb.total_cost
                self.total_api_tokens += cb.total_tokens
                cost = {"cost": f"{cb.total_cost:.8f}", "tokens": cb.total_tokens}

                # Check if current token almost exceeded limit, then try to fade the previous memory
                print(f"tokens: {cb.total_tokens}")
                if cb.total_tokens > 8000:
                    self.fade_memory()

            self.messages.extend([human_query, response])

        else:
            response = SystemMessage(content="No context provided, hence no response")
        return response.content, cost, sources

    async def is_trivial_query(self, query):
        prompt = PromptTemplate(
            template=r"As a teaching assistant for this course, you do not have the authority to approve any student "
                     r"requests. All decisions regarding such requests are exclusively made by the course instructor. "
                     r"Please assess whether the following Query requires approval from the instructor. "
                     r"Respond with 'YES' if it requires instructor approval, or 'NO' if it does not.\n\n"
                     r"Query: {query}",
            input_variables=["query"]
        )
        chain = prompt | self.llm
        result = chain.ainvoke({"query": query})
        if result == "YES":
            # it is not trivial, requires instructor approval
            return False
        # it is trivial, does not require instructor approval
        return True

    async def get_two_llm_response(self, query):
        (answer, token_cost, sources), is_trivial = await asyncio.gather(
            self.answer_this(query=query),
            self.is_trivial_query(query)
        )

    def fade_memory(self):
        self.messages.pop(1)



    def evaluate(self, response):
        prompt = PromptTemplate(
            template=r"As an assistant who is good at evaluating an LLM response to a user query, evaluate the "
                     r"following response to a query:\n\n"
                     r"Response: {response}\n\n"
                     r"Your task is to determine if the response suggested the user meets any of the following "
                     r"five conditions:"
                     r"1. Check information on NTULean or contact course instructor for more information; OR"
                     r"2. Reach out to the course coordinators, instructors or TA for information; OR"
                     r"3. Check information from official channels through the official channels provided by your"
                     r"course instructor or university; OR "
                     r"4. Check with your course instructor or coordinator for more information; OR "
                     r"5. Please email course instructor to request; \n\n"
                     r"If any of the conditions is met, respond 'SUGGESTED TO REACH OUT'. "
                     r"Otherwise, respond 'NOT SUGGESTED TO REACH OUT'."
                     r"For any case, provide a reason for your classification."
                     r"{format_instructions}",
            input_variables=["response"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()},
        )

        chain = prompt | self.llm | self.parser
        result = chain.invoke({"response": response})
        if result['classification'] == "SUGGESTED TO REACH OUT":
            return True
        return False

    def create_ticket_title(self, query):
        prompt = PromptTemplate(
            template=r"As an assistant who is good summarising a user query and turn it into a title of a support "
                     r"ticket. Your task is to summarise the following query from a student into a title of a support "
                     r"ticket for the course instructor:\n\n"
                     r"Query: {query}\n\n"
                     r"Respond directly with the content of the title without any attribute headers.",
            input_variables=["response"]
        )
        chain = prompt | self.llm | StrOutputParser()
        return chain.invoke({"query": query})


def test():
    print("Starting Local Test...")
    bot = Narelle(
        deployment_name=os.environ['AZURE_OPENAI_DEPLOYMENT_NAME'],
        model_name=os.environ['AZURE_OPENAI_MODEL_NAME'],
        temperature=0
    )
    # query = input("Query : ")
    # query = ("I notice that there is a mistake in Slide 12 for AI Topic Lecture 1, Can you help to check if that "
    #          "slide is correct or it is a typo")
    # query = ("Next week I am representing school to join an international competition at Belgium, can I request for "
    #          "Make Up Quiz?")
    query = "I am not feeling well today, can I skip the class?"
    query = ("Hi there, currently I do not have any teammate for the project, can you help to assign me a team or "
             "recommend which team that is still looking for team member? I am willing to join their team")
    # query = ("My grade for Lab 5 has been adjusted recently, previously it was A but yesterday, i notice my grade for "
    #          "this lab was updated to B+. May i know what is going on there?")
    # query = "How did i do for my exams?"
    query = "Can you explain breath-first search to me?" # NOT SUGGESTED TO REACH OUT
    query = "What are the assessment components?" # NOT SUGGESTED TO REACH OUT
    query = "Can I skip any of the classes?" # SUGGEST TO REACH OUT
    query = "Can you list down the deadline for each assessments?" # NOT SUGGESTED TO REACH OUT
    query = "How many classes do we need to attend each week?" # NOT SUGGESTED TO REACH OUT
    query = "Can I bring calculator to the exam?" # NOT SUGGESTED TO REACH OUT
    query = "What if I am late for the exam?" # SUGGEST TO REACH OUT
    query = "What if I am sick on the exam day?" # SUGGEST TO REACH OUT
    query = "Write a python code for bfs algorithm"
    while query != "quit":
        answer, token_cost, sources = bot.answer_this(query=query)

        print(f"AI :{answer}")
        print(bot.evaluate(answer))
        # if bot.evaluate(query, answer[0]):
        #     print("SATISFIED REQUEST")
        # else:
        #     print("UNABLE TO SATISFY REQUEST")
        query = input("Query : ")

    for message in bot.messages:
        print(f"\n\n{message.type:6} : \n{message.content}")
    print(f"The total cost of this conversation is: {bot.total_api_cost:.6f}")


def test_create_ticket_title():
    print("Starting Local Test...")
    bot = Narelle(
        deployment_name=os.environ['AZURE_OPENAI_DEPLOYMENT_NAME'],
        model_name=os.environ['AZURE_OPENAI_MODEL_NAME'],
        temperature=0
    )
    query = "how well did i do for my exams?"
    print(bot.create_ticket_title(query=query))


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    print("[CA-SYS] Start")
    test()
    print("[CA-SYS] Agent initialized")
