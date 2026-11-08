import anyio
import os
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage
import dotenv

dotenv.load_dotenv()

# Redirect to the local router
# os.environ["ANTHROPIC_BASE_URL"] = "http://127.0.0.1:8000"
# os.environ["ANTHROPIC_AUTH_TOKEN"] = "0629"
# os.environ["ANTHROPIC_MODEL"] = "Qwen3.5-9B-MLX-4bit"

print(os.environ["ANTHROPIC_BASE_URL"])
print(os.environ["ANTHROPIC_AUTH_TOKEN"])


async def main():
    # Agentic loop: streams messages as Claude works
    async for message in query(
        prompt="execute skill 'hello-world'",  # Example prompt to execute a skill
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Edit", "Glob", "Skill"],  # Tools Claude can use
            permission_mode="acceptEdits",  # Auto-approve file edits
            cwd='./'
        ),
    ):
        # Print human-readable output
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text"):
                    print(block.text)  # Claude's reasoning
                elif hasattr(block, "name"):
                    print(f"Tool: {block.name}")  # Tool being called
        elif isinstance(message, ResultMessage):
            print(f"Done: {message.subtype}")  # Final result



if __name__ == "__main__":
    anyio.run(main)
