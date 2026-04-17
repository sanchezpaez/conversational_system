import json

from app.agent import SupportAgent
from app.config import load_environment
from app.llm import LLMClient

TEST_QUERIES = [
    "Where is my order AB-123?",
    "Can you move booking for order 7821 to 2026-04-02?",
    "I have a complaint about your website experience.",
]


def run() -> None:
    load_environment()
    agent = SupportAgent(llm_client=LLMClient())

    for query in TEST_QUERIES:
        result = agent.process(query)
        print("\nQUERY:", query)
        print(json.dumps(result.model_dump(), indent=2))


if __name__ == "__main__":
    run()
