import os
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.output_parsers import StrOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field


class Result(BaseModel):
    classification: str = Field(
        description="The classification of the response, either SUGGESTED TO REACH OUT or NOT SUGGESTED TO REACH OUT"
    )
    reason: str = Field(description="The reason for the classification")


class Evaluator:
    def __init__(self, deployment_name, model_name, temperature=0):
        self.llm = AzureChatOpenAI(
            deployment_name=deployment_name,
            model_name=model_name,
            temperature=temperature
        )
        self.parser = JsonOutputParser(pydantic_object=Result)

    def evaluate(self, response):
        # prompt = ChatPromptTemplate.from_template(
        #     f"As an assistant who is good at evaluating an LLM response to a user query, evaluate the following response to the given query:\n\n"
        #     f"Query: {query}\n\n"
        #     f"Response: {response}\n\n"
        #     f"Your task is to determine if the response directly answers the query and satisfies the user's intention.\n\n"
        #     f"A response is considered 'UNABLE TO SATISFY REQUEST' if it does not provide the necessary information, deflects by stating limitations, or suggests alternative solutions without addressing the original query.\n\n"
        #     f"Examples of 'UNABLE TO SATISFY REQUEST' responses include, but are not limited to:\n"
        #     f"1. 'I'm sorry, as a course assistant, I do not have the ability to do that or I do not have such information. But you can look for instructor for more info.'\n"
        #     f"2. 'I apologize for the inconvenience. As an AI chatbot, I don't have access to specific slides, lecture materials, or scores.'\n"
        #     f"3. 'I apologize, but I don't have access to individual student scores for exams.'\n"
        #     f"4. 'Unfortunately, I cannot provide specific feedback on assignments.'\n"
        #     f"5. 'Please contact your instructor for detailed information on your performance.'\n\n"
        #     f"Scenarios of 'UNABLE TO SATISFY REQUEST':\n\n"
        #     f"Scenario 1:\n"
        #     f"Query: 'Can you explain 'ABC' to me?'\n"
        #     f"Response: 'I'm sorry, I do not have info about 'ABC'. But you can look for 'DEF' to get your answer.'\n\n"
        #     f"Scenario 2:\n"
        #     f"Query: 'Can you do 'ABC' for me?'\n"
        #     f"Response: 'I apologize, as a course assistant, I do not have access to 'ABC'. But I can recommend you to do 'DEF'.'\n\n"
        #     f"Scenario 3:\n"
        #     f"Query: 'Why do I get 'ABC', can you change it for me?'\n"
        #     f"Response: 'I apologize, as a AI Chatbot, I do not have access to 'ABC' and I cannot modify it. But I "
        #     f"can recommend you to reach out to 'DEF' where you can find 'ABC'.'\n\n"
        #     f"If the response is trivial, directly answers the query, and satisfies the user's intention without suggesting alternate solution or redirecting query, respond with 'SATISFIED "
        #     f"REQUEST WITHOUT GIVING ALTERNATE SOLUTION'. Otherwise, respond with 'UNABLE TO SATISFY REQUEST'. For any case, provide a reason for your "
        #     f"classification."
        # )
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
        print(chain.invoke({"response": response}))


def test():
    evaluator = Evaluator(
        deployment_name=os.environ['AZURE_OPENAI_DEPLOYMENT_NAME'],
        model_name=os.environ['AZURE_OPENAI_MODEL_NAME'],
        temperature=0
    )

    query = "I think I do well on the recent quiz, but my score is low, may I know which part I did not do well?"
    response = ("I'm sorry, but as a course assistant, I don't have access to individual quiz scores or the ability to "
                "provide specific feedback on quiz performance. For information regarding your quiz score and "
                "feedback, I recommend reaching out to your Lab TA or the course coordinator. They will be able to "
                "assist you and provide you with the necessary information.")

    query = "I think I do well on the recent quiz, but my score is low, may I know which part I did not do well?"
    response = ("I apologize, but as a course assistant, I don't have access to individual student's quiz scores or the "
               "specific breakdown of their performance in each part of the quiz. The quiz scores and feedback are "
               "typically provided by your instructor or through the online platform where the quiz was conducted. I "
               "recommend checking the feedback provided by your instructor or reaching out to them directly to "
               "inquire about the specific areas where you may have not performed well. They will be able to provide "
               "you with more detailed information and guidance on how to improve.")

    response = ("I'm sorry, but as a course assistant, I don't have access to individual student's exam grades. You "
                "can check your exam grades through the official channels provided by your university or course "
                "coordinator.")

    response = ("I'm sorry, but as a course assistant, I don't have access to individual student's exam grades. You "
                "will need to check with your instructor or refer to the grading system provided by your university "
                "to determine how well you did in your exams.")

    response = ("Yes, you can request for a Make-Up Quiz if you are unable to attend the scheduled quiz due to "
                "representing the school in an international competition. Please email Smitha K G (smitha@ntu.edu.sg) "
                "to request for the Make-Up Quiz. Make sure to provide a valid reason and any supporting documents "
                "for your request. The details of the Make-Up Quiz will be communicated to you separately.")



    # query = ("I notice that there is a mistake in Slide 12 for AI Topic Lecture 1, Can you help to check if that slide "
    #          "is correct or it is a typo.")
    # response = ("I apologize for the inconvenience. As an AI chatbot, I don't have access to specific slides or "
    #             "lecture materials. However, if you believe there is a mistake on Slide 12 for AI Topic Lecture 1, "
    #             "I recommend reaching out to your instructor or TA for clarification. They will be able to review the "
    #             "slide and provide you with the correct information.")

    # query = ("My grade for Lab 5 has been adjusted recently, previously it was A but yesterday, i notice my grade for "
    #          "this lab was updated to B+. May i know what is going on there?")
    # response = ("I apologize for the confusion regarding your grade for Lab 5. As a course assistant, I don't have "
    #             "access to individual student grades or the ability to make changes to them. I recommend reaching out "
    #             "to your Lab TA or the course coordinator, Dr. Smitha K G (smitha@ntu.edu.sg), for clarification on "
    #             "the adjustment made to your grade. They will be able to provide you with the necessary information "
    #             "and address any concerns you may have.")

    # query = "how did i do for exams"
    # response = ("I'm sorry, but as a course assistant, I don't have access to individual student exam results. You "
    #             "will need to check your exam results through the official channels provided by your university or "
    #             "course coordinator.")

    # query = "how are my exams"
    # response = ("I apologize, but as a course assistant, I don't have access to individual student's exam grades. You "
    #             "can check your exam grades on NTULearn or contact your course instructor for more information.")

    evaluator.evaluate(response)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    test()
