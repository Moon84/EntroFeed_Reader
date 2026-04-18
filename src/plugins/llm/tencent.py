# -*- coding: utf-8 -*-
"""Tencent Hunyuan (腾讯混元) LLM Plugin for EntroFeed."""

import hashlib
import hmac
import time
from typing import ClassVar, Dict, List

import requests
from pydantic import Field

from src.handlers import LLMHandler
from src.metrics import record_llm_request, record_token_usage
from src.models.feed import Feed, FeedEntry
from src.plugins.llm import ModelWrapperBase, LLMPluginRegistry


class TencentLLMHandler(ModelWrapperBase, LLMHandler):
    """Tencent Hunyuan handler using TC3-HMAC-SHA256 auth."""

    secret_id: str = Field(default="")
    secret_key: str = Field(default="")
    model: str = Field(default="hunyuan-pro")

    id: ClassVar[str] = "tencent"
    required_env: ClassVar[List[str]] = ["TENCENT_SECRET_ID", "TENCENT_SECRET_KEY"]

    def _generate_signature(self, payload: str, timestamp: int) -> str:
        """Generate TC3-HMAC-SHA256 signature."""
        # This is a simplified version - full implementation would use Tencent's TC3 auth
        service = "hunyuan"
        host = "hunyuan.tencentcloudapi.com"
        algorithm = "TC3-HMAC-SHA256"

        # Build canonical request
        http_request_method = "POST"
        canonical_uri = "/"
        canonical_query_string = ""
        canonical_headers = f"content-type:application/json\nhost:{host}\n"
        signed_headers = "content-type;host"

        hashed_request_payload = hashlib.sha256(payload.encode()).hexdigest()

        canonical_request = (
            f"{http_request_method}\n"
            f"{canonical_uri}\n"
            f"{canonical_query_string}\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{hashed_request_payload}"
        )

        # Build string to sign
        credential_scope = f"{timestamp:%Y%m%d}/{service}/tc3_request"
        hashed_canonical_request = hashlib.sha256(canonical_request.encode()).hexdigest()

        string_to_sign = (
            f"{algorithm}\n"
            f"{timestamp}\n"
            f"{credential_scope}\n"
            f"{hashed_canonical_request}"
        )

        # Calculate signature
        secret_date = hmac.new(
            f"TC3{self.secret_key}".encode(),
            f"{timestamp:%Y%m%d}".encode(),
            hashlib.sha256
        ).digest()

        secret_service = hmac.new(
            secret_date,
            service.encode(),
            hashlib.sha256
        ).digest()

        secret_signing = hmac.new(
            secret_service,
            "tc3_request".encode(),
            hashlib.sha256
        ).digest()

        signature = hmac.new(
            secret_signing,
            string_to_sign.encode(),
            hashlib.sha256
        ).hexdigest()

        return signature

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Make chat completion call to Tencent Hunyuan."""
        import json

        # Build request payload
        payload = {
            "Model": self.model,
            "Messages": [{"Role": m["role"], "Content": m["content"]} for m in messages],
        }
        payload.update(kwargs)

        payload_str = json.dumps(payload)
        timestamp = int(time.time())

        headers = {
            "Content-Type": "application/json",
            "Host": "hunyuan.tencentcloudapi.com",
            "X-TC-Action": "ChatCompletions",
            "X-TC-Version": "2023-09-01",
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Region": "ap-guangzhou",
        }

        start_time = self._last_call_start = self._get_time()
        try:
            response = requests.post(
                "https://hunyuan.tencentcloudapi.com",
                headers=headers,
                data=payload_str,
                timeout=60
            )

            result = response.json()

            if "Error" in result:
                raise Exception(f"Tencent API error: {result['Error']}")

            output = result.get("Response", {}).get("Choices", [{}])[0]
            content = output.get("Message", {}).get("Content", "")

            # Record metrics (usage info may be in response)
            usage = result.get("Response", {}).get("Usage", {})
            input_tokens = usage.get("PromptTokens", 0)
            output_tokens = usage.get("CompletionTokens", 0)

            if input_tokens or output_tokens:
                record_token_usage(self.model, input_tokens, output_tokens)

            duration = self._get_time() - start_time
            record_llm_request(self.id, self.model, True, duration)

            return content
        except Exception:
            duration = self._get_time() - start_time
            record_llm_request(self.id, self.model, False, duration)
            raise

    def summarize(self, feed: Feed, entry: FeedEntry, mk: str) -> str:
        """Summarize content using Tencent Hunyuan."""
        return self._make_chat_call(
            system=self.summarization_system_prompt,
            prompt=self.get_summarization_prompt(mk)
        )

    def _get_time(self) -> float:
        """Get current time for metrics."""
        return time.time()


# Auto-register on import
LLMPluginRegistry.register(TencentLLMHandler)
