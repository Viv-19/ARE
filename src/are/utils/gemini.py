"""
Centralized Gemini API Client for ARE
Supports three operating modes:
- Judgment Mode (NODE-0, 1, 3, 6): Very constrained, strict JSON
- Execution Support Mode (NODE-5): Semi-constrained, code + logs
- Communication Mode (NODE-8): Expressive but factual, Markdown + JSON
"""

import os
import json
import logging
from typing import Optional, Dict, Any, Literal

# Configure logging for Gemini module
logger = logging.getLogger(__name__)

# Lazy import to avoid dependency issues
_ChatGoogleGenerativeAI = None
_HumanMessage = None

def _get_langchain_gemini():
    """Lazy load langchain_google_genai to avoid import errors."""
    global _ChatGoogleGenerativeAI, _HumanMessage
    if _ChatGoogleGenerativeAI is None:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            from langchain_core.messages import HumanMessage
            _ChatGoogleGenerativeAI = ChatGoogleGenerativeAI
            _HumanMessage = HumanMessage
            logger.info("✓ langchain-google-genai loaded successfully")
        except ImportError:
            logger.error("✗ langchain-google-genai not installed. Run: pip install langchain-google-genai")
            return None, None
    return _ChatGoogleGenerativeAI, _HumanMessage


class GeminiClient:
    """
    Mode-aware Gemini API client using LangChain for stability.
    """
    
    MODE_CONFIGS = {
        "judgment": {
            "temperature": 0.1,
            "top_p": 0.8,
            "max_output_tokens": 2048,
        },
        "execution_support": {
            "temperature": 0.3,
            "top_p": 0.9,
            "max_output_tokens": 8192,
        },
        "communication": {
            "temperature": 0.5,
            "top_p": 0.95,
            "max_output_tokens": 16384,
        }
    }
    
    def __init__(self, model_name: str = "gemini-1.5-flash"):
        self.model_name = model_name
        self._llm_instances = {}  # Cache instances per mode
        self._initialized = False
        
    def _get_llm(self, mode: str):
        """Get or create a LangChain LLM instance for the given mode."""
        if mode in self._llm_instances:
            return self._llm_instances[mode]
            
        ChatModel, _ = _get_langchain_gemini()
        if ChatModel is None:
            return None
            
        from ..config import GEMINI_API_KEY
        api_key = GEMINI_API_KEY or os.environ.get("GOOGLE_API_KEY")
        
        if not api_key:
            logger.error("✗ GEMINI_API_KEY not set.")
            return None
            
        config = self.MODE_CONFIGS.get(mode, self.MODE_CONFIGS["judgment"])
        
        try:
            llm = ChatModel(
                model=self.model_name,
                google_api_key=api_key,
                temperature=config["temperature"],
                top_p=config["top_p"],
                max_output_tokens=config["max_output_tokens"]
            )
            self._llm_instances[mode] = llm
            return llm
        except Exception as e:
            logger.error(f"✗ Failed to create LLM for mode {mode}: {e}")
            return None

    def is_available(self) -> bool:
        """Check if Gemini API is configured."""
        from ..config import GEMINI_API_KEY
        return bool(GEMINI_API_KEY or os.environ.get("GOOGLE_API_KEY"))
    
    def generate(
        self,
        prompt: str,
        mode: Literal["judgment", "execution_support", "communication"] = "judgment",
        expect_json: bool = True,
        retry_count: int = 5
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a response from Gemini using LangChain.
        """
        llm = self._get_llm(mode)
        if not llm:
            return None
            
        _, HumanMsg = _get_langchain_gemini()
        
        logger.info(f"[Gemini] Generating response in '{mode}' mode")
        
        last_error = None
        for attempt in range(retry_count + 1):
            try:
                response = llm.invoke([HumanMsg(content=prompt)])
                
                if not response.content:
                    logger.warning(f"[Gemini] Empty response on attempt {attempt + 1}")
                    continue
                    
                text = response.content.strip()
                logger.info(f"[Gemini] ✓ Got response ({len(text)} chars)")
                
                if expect_json:
                    # Clean markdown formatting if present
                    if "```json" in text:
                        text = text.split("```json")[-1].split("```")[0]
                    elif "```" in text:
                        text = text.split("```")[-1].split("```")[0]
                    text = text.strip()
                    
                    try:
                        result = json.loads(text)
                        return result
                    except json.JSONDecodeError as e:
                        # Attempt heuristic extraction
                        import re
                        json_match = re.search(r'\{.*\}', text, re.DOTALL)
                        if json_match:
                            try:
                                return json.loads(json_match.group())
                            except:
                                pass
                        last_error = e
                        continue
                else:
                    return {"content": text}
                    
            except Exception as e:
                import time
                import random
                
                error_str = str(e).lower()
                is_rate_limit = "429" in error_str or "rate limit" in error_str or "quota" in error_str
                
                if is_rate_limit and attempt < retry_count:
                    # Exponential backoff with jitter
                    wait_time = (2 ** attempt) + random.uniform(0, 1) + 2 # Start with ~3s, then ~5s, ~7s...
                    logger.warning(f"[Gemini] ⏳ Rate limit (429) hit. Retrying in {wait_time:.1f}s... (Attempt {attempt+1}/{retry_count+1})")
                    time.sleep(wait_time)
                    continue
                
                logger.error(f"[Gemini] ✗ Generation failed (attempt {attempt + 1}): {e}")
                last_error = e
                if not is_rate_limit: # For non-rate-limit errors, maybe fail faster or still retry?
                    # Let's still retry for connectivity issues, but maybe shorter wait
                    time.sleep(1)
                continue
        
        return None


# Global client instance (lazy initialization)
_client: Optional[GeminiClient] = None

def get_client(model_name: str = "gemini-1.5-flash") -> GeminiClient:
    """Get or create the global Gemini client."""
    global _client
    if _client is None:
        _client = GeminiClient(model_name)
    return _client


def call_gemini(
    prompt: str,
    mode: Literal["judgment", "execution_support", "communication"] = "judgment",
    expect_json: bool = True,
    fallback: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Convenience function to call Gemini with automatic fallback.
    
    Args:
        prompt: The full prompt
        mode: Operating mode
        expect_json: Whether to parse as JSON
        fallback: Value to return if Gemini fails
        
    Returns:
        Gemini response or fallback value
    """
    from ..config import USE_GEMINI
    
    if not USE_GEMINI:
        logger.info("[Gemini] Disabled via config (USE_GEMINI=false). Using fallback.")
        return fallback
    
    logger.info(f"[Gemini] Calling in '{mode}' mode...")
    client = get_client()
    result = client.generate(prompt, mode=mode, expect_json=expect_json)
    
    if result is None:
        logger.warning("[Gemini] Call failed. Using fallback.")
        return fallback
    
    logger.info("[Gemini] ✓ Call successful")
    return result
