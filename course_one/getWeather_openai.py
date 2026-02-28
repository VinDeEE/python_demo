import os
import sys
from pathlib import Path

from langchain.agents import create_agent


def load_env_file() -> None:
    """Load key=value pairs from the project root .env file if it exists."""
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_env_file()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print(
        "Missing OPENAI_API_KEY. "
        "Please set it in your environment or .env and rerun the script.",
        file=sys.stderr,
    )
    print(
        "PowerShell example: $env:OPENAI_API_KEY='your_api_key_here'",
        file=sys.stderr,
    )
    raise SystemExit(1)


def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"


agent = create_agent(
    model="openai:gpt-4o-mini",
    tools=[get_weather],
    system_prompt="You are a helpful assistant",
)

# Run the agent
result = agent.invoke(
    {"messages": [{"role": "user", "content": "what is the weather in sf"}]}
)

print(result)
