import anyio
import os
from claude_code_sdk import query, ClaudeCodeOptions

from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage

# Redirect to the local router
os.environ["ANTHROPIC_BASE_URL"] = "http://127.0.0.1:3456"
os.environ["ANTHROPIC_AUTH_TOKEN"] = "ollama"

print(os.environ["ANTHROPIC_BASE_URL"])
print(os.environ["ANTHROPIC_AUTH_TOKEN"])

# async def main():
#     # Options can specify models defined in your router's config.json
#     options = ClaudeCodeOptions(
#         model="ollama,minimax-m2.5:cloud", # Example routed model
#         max_turns=1
#     )

#     async for message in query(prompt="Analyze this code", options=options):
#         print(message)

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
