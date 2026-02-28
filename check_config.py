import os
from src.are.config import USE_GEMINI, GEMINI_MODEL, GEMINI_API_KEY, USE_MOCK
from src.are.utils.gemini import call_gemini

print("--- CONFIG CHECK ---")
print(f"USE_GEMINI: {USE_GEMINI}")
print(f"GEMINI_MODEL: {GEMINI_MODEL}")
print(f"GEMINI_API_KEY: {GEMINI_API_KEY[:8]}...")
print(f"USE_MOCK: {USE_MOCK}")
print("--- TEST CALL ---")

res = call_gemini("test", fallback={"status": "failed"})
print(f"Result: {res}")
