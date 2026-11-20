
from pathlib import Path
import os

from dotenv import load_dotenv

from core.model_client import ModelClient


ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

# Only this diagnostic script uses API mode.
# The normal project can remain in MOCK mode.
os.environ["AI_MODE"] = "api"

client = ModelClient()

print("Testing DeepSeek API...")

result = client.generate(
    system_prompt="You are a helpful assistant.",
    user_prompt="Reply with exactly: OK",
    max_tokens=32,
)

print("API Response:", result)
print("API Usage:", client.last_usage)
print("Connection test completed.")
