import deepeval
from deepeval import evaluate
from deepeval.metrics import ContextualRelevancyMetric
from deepeval.test_case import LLMTestCase
import os
from dotenv import load_dotenv

load_dotenv()


def main():
    # Replace this with the actual output from your LLM application
    actual_output = "We offer a 30-day full refund at no extra cost."

    # Replace this with the actual retrieved context from your RAG pipeline
    retrieval_context = ["All customers are eligible for a 30 day full refund at no extra cost."]

    metric = ContextualRelevancyMetric(
        threshold=0.7,
        model="gpt-4",
        include_reason=True
    )
    test_case = LLMTestCase(
        input="What if these shoes don't fit?",
        actual_output=actual_output,
        retrieval_context=retrieval_context
    )

    metric.measure(test_case)
    print(metric.score)
    print(metric.reason)

    # or evaluate test cases in bulk
    evaluate([test_case], [metric])


if __name__ == "__main__":
    deepeval.login_with_confident_api_key(os.environ['CONFIDENT_API_KEY'])
    main()
