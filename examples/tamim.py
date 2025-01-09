#!/usr/bin/env python3

import logging
from tulip_agent import NaiveTulipAgent, ToolLibrary, MinimalTulipAgent

from tamims import capital, language

# Set logger to INFO to see the agent's steps
logging.basicConfig(level=logging.INFO)



# Tool library setup
GENERAL_FUNCTIONS = [
    "capital",
    "language",
]


tulip = ToolLibrary(
    chroma_sub_dir="examples/",
    file_imports=[("tamims", [])],
    # file_imports=[("calculator", ["add", "subtract", "square_root"])],
    # file_imports=[("math_tools", [])],
)


def main():
    # Initialize NaiveTulipAgent
    agent = MinimalTulipAgent(
        tool_library=tulip,
        top_k_functions=3,
        search_similarity_threshold=0.5,
    )

    # Query example
    query = "What is the capital of France?"
    response = agent.query(query)
    print(f"Query: {query}\nResponse: {response}")


if __name__ == "__main__":
    main()
