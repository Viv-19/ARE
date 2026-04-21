"""
Groq Adapter -- concrete LLMPort implementation using REST API.

Optimized for cheap/fast models using the Groq API.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Dict, Optional
import requests

from are.ports.llm_port import LLMMode, LLMPort, LLMResponse

logger = logging.getLogger(__name__)

_MODE_CONFIGS: Dict[LLMMode, Dict[str, Any]] = {
    LLMMode.JUDGMENT: {"temperature": 0.1, "top_p": 0.8},
    LLMMode.EXECUTION_SUPPORT: {"temperature": 0.3, "top_p": 0.9},
    LLMMode.COMMUNICATION: {"temperature": 0.5, "top_p": 0.95},
}


class GroqAdapter(LLMPort):
    """Production Groq adapter using the Groq REST API directly."""

    def __init__(
        self,
        model: str = "llama-3.3-70b-versatile",
        api_key: str = "",
        max_retries: int = 3,
    ):
        self._model_name = model
        self._api_key = api_key
        self._max_retries = max_retries
        self._url = "https://api.groq.com/openai/v1/chat/completions"

    # ── Port interface ───────────────────────────────────────────────

    def generate(
        self,
        prompt: str,
        *,
        mode: LLMMode = LLMMode.JUDGMENT,
        expect_json: bool = True,
    ) -> LLMResponse:
        
        config = _MODE_CONFIGS[mode]
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self._model_name,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": config["temperature"],
            "top_p": config["top_p"],
        }
        
        if expect_json:
            payload["response_format"] = {"type": "json_object"}

        last_error = ""

        for attempt in range(self._max_retries + 1):
            start = time.perf_counter()
            try:
                resp = requests.post(self._url, headers=headers, json=payload, timeout=30)
                latency = (time.perf_counter() - start) * 1000
                
                if resp.status_code == 429:
                    wait = 5.0
                    last_error = f"Rate limit (429): {resp.text}"
                    logger.warning("[Groq] Rate limit, waiting %.1fs", wait)
                    time.sleep(wait)
                    continue
                    
                resp.raise_for_status()
                data = resp.json()
                
                text = data["choices"][0]["message"]["content"]
                tokens = data.get("usage", {}).get("total_tokens", len(text.split()))

                if not text:
                    last_error = "Empty response"
                    continue

                parsed = None
                if expect_json:
                    parsed = self._extract_json(text)
                    if parsed is None:
                        last_error = "JSON parse failure"
                        continue

                logger.info(
                    "[Groq] OK mode=%s latency=%.0fms tokens=~%d",
                    mode.name, latency, tokens,
                )
                return LLMResponse(
                    content=text,
                    parsed=parsed,
                    model=self._model_name,
                    tokens_used=tokens,
                    latency_ms=latency,
                    success=True,
                )

            except Exception as exc:
                last_error = str(exc)
                logger.error("[Groq] Attempt %d failed: %s", attempt + 1, last_error)
                if "429" not in last_error:
                    time.sleep(2.0)

        return self._fail(f"All retries exhausted. Last: {last_error}")

    def is_available(self) -> bool:
        if not self._api_key:
            return False
        return True

    @property
    def provider_name(self) -> str:
        return f"Groq ({self._model_name})"

    # ── Internal helpers ─────────────────────────────────────────────

    def _fail(self, error: str) -> LLMResponse:
        return LLMResponse(
            content="",
            parsed=None,
            model=self._model_name,
            tokens_used=0,
            latency_ms=0,
            success=False,
            error=error,
        )

    @staticmethod
    def _extract_json(text: str) -> Optional[Dict]:
        """Best-effort JSON extraction from potentially markdown-wrapped text."""
        clean = text
        if "```json" in clean:
            clean = clean.split("```json")[-1].split("```")[0]
        elif "```" in clean:
            parts = clean.split("```")
            if len(parts) >= 3:
                clean = parts[1]
        clean = clean.strip()

        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", clean, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        return None
