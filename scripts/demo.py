"""Interactive demo of the support agent using mocked LLM backend."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add parent directory to path so app module can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agent import SupportAgent
from app.models import EntityExtraction, IntentDecision


def create_mock_llm():
    """Create a mock LLM client that doesn't call OpenAI."""
    import re

    client = MagicMock()

    def mock_classify_intent(message: str) -> IntentDecision:
        message_lower = message.lower()
        if "order" in message_lower and ("where" in message_lower or "status" in message_lower):
            return IntentDecision(intent="order_status")
        elif "move" in message_lower or "change" in message_lower or "reschedule" in message_lower:
            return IntentDecision(intent="change_booking")
        else:
            return IntentDecision(intent="fallback")

    def mock_extract_entities(message: str) -> EntityExtraction:
        order_id = None
        date = None

        order_pattern = r"order\s+([\w-]+)"
        order_match = re.search(order_pattern, message, re.IGNORECASE)
        if order_match:
            order_id = order_match.group(1)

        date_pattern = r"(\d{4}-\d{2}-\d{2})"
        date_match = re.search(date_pattern, message)
        if date_match:
            date = date_match.group(1)

        return EntityExtraction(order_id=order_id, date=date)

    client.classify_intent = mock_classify_intent
    client.extract_entities = mock_extract_entities

    return client


def run_interactive_demo() -> None:
    """Run interactive conversation loop with the support agent."""
    print("\n" + "=" * 70)
    print("PARLOA CUSTOMER SUPPORT AI AGENT - INTERACTIVE DEMO")
    print("=" * 70)
    print("\nThis is a demo using mocked LLM (no OpenAI API key needed).")
    print("\nExample queries:")
    print("  - 'Where is my order AB-123?'")
    print("  - 'Can you move my booking order 7821 to 2026-04-15?'")
    print("  - 'I have a complaint about your website.'")
    print("\nType 'exit' to quit.\n")

    mock_llm = create_mock_llm()
    agent = SupportAgent(llm_client=mock_llm)

    while True:
        try:
            user_input = input("You: ").strip()

            if user_input.lower() in ("exit", "quit"):
                print("\nGoodbye!\n")
                break

            if not user_input:
                print("Please enter a message.\n")
                continue

            result = agent.process(user_input)

            print(f"\nAgent: {result.reply}")
            print(f"  [Intent: {result.intent}]")
            if result.entities.order_id or result.entities.date:
                print(f"  [Entities: order_id={result.entities.order_id}, date={result.entities.date}]")
            print()

        except KeyboardInterrupt:
            print("\n\nGoodbye!\n")
            break
        except Exception as error:
            print(f"\nError: {error}\n")


def run_batch_demo() -> None:
    """Run demo with predefined queries (non-interactive)."""
    queries = [
        "Where is my order AB-123?",
        "Can you move booking for order 7821 to 2026-04-02?",
        "I have a complaint about your website.",
        "Check status of order XYZ-999",
        "Reschedule my delivery to next Thursday",
    ]

    print("\n" + "=" * 70)
    print("PARLOA CUSTOMER SUPPORT AI AGENT - BATCH DEMO")
    print("=" * 70)
    print("\nRunning predefined queries with mocked LLM:\n")

    mock_llm = create_mock_llm()
    agent = SupportAgent(llm_client=mock_llm)

    for query in queries:
        result = agent.process(query)
        print(f"📩 User: {query}")
        print(f"🤖 Agent: {result.reply}")
        print(f"   Intent: {result.intent}")
        print(f"   Backend: {result.backend_result.get('code', 'unknown')}")
        print()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--batch":
        run_batch_demo()
    else:
        run_interactive_demo()
