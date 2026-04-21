"""
Gemini Adapter -- concrete LLMPort implementation using google.genai SDK.

Uses the modern google-genai SDK directly (NOT langchain-google-genai)
to avoid the broken transformers import chain on Windows.

FREE TIER OPTIMISED:
  - 4-second minimum interval between calls (stays within 15 RPM)
  - Circuit breaker: after 2 consecutive 429s, fail fast for 60s
  - Max 2 retries per call (not 5) to avoid blocking the pipeline
"""

from __future__ import annotations

import json
import logging
import random
import re
import time
from typing import Any, Dict, Optional

from are.ports.llm_port import LLMMode, LLMPort, LLMResponse

logger = logging.getLogger(__name__)


_MODE_CONFIGS: Dict[LLMMode, Dict[str, Any]] = {
    LLMMode.JUDGMENT: {"temperature": 0.1, "top_p": 0.8, "max_output_tokens": 2048},
    LLMMode.EXECUTION_SUPPORT: {"temperature": 0.3, "top_p": 0.9, "max_output_tokens": 8192},
    LLMMode.COMMUNICATION: {"temperature": 0.5, "top_p": 0.95, "max_output_tokens": 16384},
}


class GeminiAdapter(LLMPort):
    """Production Gemini adapter using ``google.genai`` SDK directly.

    Optimised for the free tier with rate-limit awareness and a circuit
    breaker that avoids burning time on retries when quota is exhausted.
    """

    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        api_key: str = "",
        max_retries: int = 2,  # Only 2 retries for free tier
    ):
        self._model_name = model
        self._api_key = api_key
        self._max_retries = max_retries
        self._client = None
        # Rate-limit tracking
        self._last_call_time: float = 0.0
        self._min_interval: float = 4.0  # seconds between calls (15 RPM)
        self._call_count: int = 0
        # Circuit breaker: if we got 429'd recently, don't even try
        self._circuit_open_until: float = 0.0

    def _get_client(self):
        """Lazy-initialise the genai client."""
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self._api_key)
            logger.info("[Gemini] Client initialised for model=%s", self._model_name)
        return self._client

    # ── Port interface ───────────────────────────────────────────────

    def generate(
        self,
        prompt: str,
        *,
        mode: LLMMode = LLMMode.JUDGMENT,
        expect_json: bool = True,
    ) -> LLMResponse:
        # ── Circuit breaker check ────────────────────────────────────
        now = time.perf_counter()
        if now < self._circuit_open_until:
            remaining = self._circuit_open_until - now
            logger.warning("[Gemini] Circuit open, skipping. %.0fs until retry.", remaining)
            return self._fail("Rate limit circuit breaker open (free tier quota exhausted)")

        try:
            client = self._get_client()
        except Exception as exc:
            logger.error("[Gemini] Client init failed: %s", exc)
            return self._fail(f"Client init failed: {exc}")

        from google.genai import types

        config = _MODE_CONFIGS[mode]
        gen_config = types.GenerateContentConfig(
            temperature=config["temperature"],
            top_p=config["top_p"],
            max_output_tokens=config["max_output_tokens"],
        )

        last_error = ""
        rate_limit_hits = 0

        for attempt in range(self._max_retries + 1):
            # ── Proactive rate limiting ──────────────────────────────
            now = time.perf_counter()
            elapsed_since_last = now - self._last_call_time
            if elapsed_since_last < self._min_interval and self._last_call_time > 0:
                wait = self._min_interval - elapsed_since_last
                time.sleep(wait)
            self._last_call_time = time.perf_counter()
            self._call_count += 1

            start = time.perf_counter()
            try:
                response = client.models.generate_content(
                    model=self._model_name,
                    contents=prompt,
                    config=gen_config,
                )
                latency = (time.perf_counter() - start) * 1000
                text = (response.text or "").strip()

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
                    "[Gemini] OK mode=%s latency=%.0fms tokens=~%d",
                    mode.name, latency, len(text.split()),
                )
                return LLMResponse(
                    content=text,
                    parsed=parsed,
                    model=self._model_name,
                    tokens_used=len(text.split()),
                    latency_ms=latency,
                    success=True,
                )

            except Exception as exc:
                latency = (time.perf_counter() - start) * 1000
                error_str = str(exc).lower()
                is_rate = any(k in error_str for k in ("429", "rate limit", "quota", "resource_exhausted"))

                if is_rate:
                    rate_limit_hits += 1
                    if rate_limit_hits >= 2:
                        # Open circuit breaker for 60 seconds
                        self._circuit_open_until = time.perf_counter() + 60.0
                        logger.warning(
                            "[Gemini] 2x 429 -> circuit breaker OPEN for 60s. Falling back to deterministic."
                        )
                        return self._fail("Rate limit: free tier quota exhausted, using fallback")

                    if attempt < self._max_retries:
                        wait = 5.0 + random.uniform(0, 2)
                        logger.warning("[Gemini] 429, retry in %.1fs (%d/%d)", wait, attempt + 1, self._max_retries)
                        time.sleep(wait)
                        continue

                last_error = str(exc)[:200]
                logger.error("[Gemini] Attempt %d failed: %s", attempt + 1, last_error)
                if not is_rate:
                    break  # Non-rate-limit errors don't improve with retry

        return self._fail(f"All retries exhausted. Last: {last_error}")

    def is_available(self) -> bool:
        if not self._api_key:
            return False
        # Also check circuit breaker
        if time.perf_counter() < self._circuit_open_until:
            return False
        return True

    @property
    def provider_name(self) -> str:
        return f"Gemini ({self._model_name})"

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
