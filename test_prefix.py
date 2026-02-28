import os
import json
from dotenv import load_dotenv
load_dotenv()
from src.are.utils.gemini import GeminiClient

client = GeminiClient(model_name="models/gemini-2.0-flash-lite")
res = client.generate("Hello", mode="judgment", expect_json=False)
print(f"Result: {res}")
