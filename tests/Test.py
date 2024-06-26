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
        # "Can you list down the deadline for each assessments?",
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
    import os
    from Narelle import Narelle
    from dotenv import load_dotenv
    from langchain_community.callbacks import get_openai_callback
    load_dotenv()

    print("Starting Unit Test...")
    test_single_input()
