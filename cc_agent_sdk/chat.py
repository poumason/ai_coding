import anyio
import dotenv
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, ResultMessage

dotenv.load_dotenv()

SESSION_ID = "chat-session"


async def print_response(client: ClaudeSDKClient) -> bool:
    """Stream and print Claude's response. Returns True when the turn is done."""
    async for message in client.receive_response():
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text"):
                    print(f"\nClaude: {block.text}", end="", flush=True)
        elif isinstance(message, ResultMessage):
            print()  # newline after response
            return True
    return True


async def main():
    options = ClaudeAgentOptions(
        permission_mode="dontAsk",
        cwd="./",
    )

    print("Chat started. Type 'exit' or 'quit' to end the session.\n")

    async with ClaudeSDKClient(options=options) as client:
        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break

            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit"):
                print("Goodbye!")
                break

            await client.query(user_input, session_id=SESSION_ID)
            await print_response(client)


if __name__ == "__main__":
    anyio.run(main)
