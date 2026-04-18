# -*- coding: utf-8 -*-
"""Tests for Metrics module."""

import pytest

from src.metrics import (
    LLM_PRICING,
    PluginCheckResult,
    record_token_usage,
    record_llm_request,
    record_llm_cost,
    record_plugin_init,
    record_plugin_shutdown,
    record_plugin_check,
    record_plugin_error,
    get_metrics,
    get_content_type,
)


class TestPluginCheckResult:
    """Test PluginCheckResult dataclass."""

    def test_create_with_all_fields(self):
        """Test creating PluginCheckResult with all fields."""
        result = PluginCheckResult(
            available=True, reason="Success", missing_env=["API_KEY"]
        )
        assert result.available is True
        assert result.reason == "Success"
        assert result.missing_env == ["API_KEY"]

    def test_create_with_defaults(self):
        """Test creating PluginCheckResult with defaults."""
        result = PluginCheckResult(available=True)
        assert result.available is True
        assert result.reason is None
        assert result.missing_env == []

    def test_post_init_defaults_missing_env(self):
        """Test that missing_env defaults to empty list."""
        result = PluginCheckResult(available=False)
        assert result.missing_env == []


class TestLLMPricing:
    """Test LLM pricing configuration."""

    def test_llm_pricing_exists(self):
        """Test LLM_PRICING dictionary exists."""
        assert isinstance(LLM_PRICING, dict)

    def test_dashscope_pricing(self):
        """Test DashScope pricing is defined."""
        assert "dashscope" in LLM_PRICING
        assert "qwen-plus" in LLM_PRICING["dashscope"]
        assert "qwen-max" in LLM_PRICING["dashscope"]

    def test_openai_pricing(self):
        """Test OpenAI pricing is defined."""
        assert "openai" in LLM_PRICING
        assert "gpt-4o-mini" in LLM_PRICING["openai"]
        assert "gpt-4o" in LLM_PRICING["openai"]

    def test_pricing_format(self):
        """Test pricing is (input, output) tuple."""
        for provider, models in LLM_PRICING.items():
            for model, (input_cost, output_cost) in models.items():
                assert isinstance(input_cost, (int, float))
                assert isinstance(output_cost, (int, float))
                assert input_cost >= 0
                assert output_cost >= 0


class TestMetricsRecording:
    """Test metrics recording functions."""

    def test_record_token_usage(self):
        """Test recording token usage doesn't raise."""
        # Should not raise
        record_token_usage(model="test-model", input_tokens=100, output_tokens=50)

    def test_record_llm_request_success(self):
        """Test recording successful LLM request."""
        record_llm_request(
            provider="test", model="test-model", success=True, duration=1.0
        )

    def test_record_llm_request_error(self):
        """Test recording failed LLM request."""
        record_llm_request(
            provider="test", model="test-model", success=False, duration=0.5
        )

    def test_record_llm_cost(self):
        """Test recording LLM cost."""
        # Should not raise
        record_llm_cost(
            provider="dashscope",
            model="qwen-plus",
            input_tokens=1000,
            output_tokens=500,
        )

    def test_record_llm_cost_unknown_provider(self):
        """Test recording cost for unknown provider doesn't raise."""
        record_llm_cost(
            provider="unknown",
            model="unknown-model",
            input_tokens=1000,
            output_tokens=500,
        )

    def test_record_plugin_init_success(self):
        """Test recording plugin init success."""
        record_plugin_init(
            plugin_type="llm", plugin_id="test-plugin", duration=0.1, success=True
        )

    def test_record_plugin_init_failure(self):
        """Test recording plugin init failure."""
        record_plugin_init(
            plugin_type="llm", plugin_id="test-plugin", duration=0.1, success=False
        )

    def test_record_plugin_shutdown(self):
        """Test recording plugin shutdown."""
        record_plugin_shutdown(plugin_type="llm", plugin_id="test-plugin")

    def test_record_plugin_check_available(self):
        """Test recording plugin check when available."""
        record_plugin_check(plugin_type="llm", plugin_id="test-plugin", available=True)

    def test_record_plugin_check_unavailable(self):
        """Test recording plugin check when unavailable."""
        record_plugin_check(
            plugin_type="llm",
            plugin_id="test-plugin",
            available=False,
            reason="Missing API key",
        )

    def test_record_plugin_error(self):
        """Test recording plugin error."""
        record_plugin_error(plugin_type="llm", plugin_id="test-plugin")


class TestMetricsOutput:
    """Test metrics output functions."""

    def test_get_metrics(self):
        """Test get_metrics returns bytes."""
        metrics = get_metrics()
        assert isinstance(metrics, bytes)
        assert len(metrics) > 0

    def test_get_content_type(self):
        """Test get_content_type returns string."""
        content_type = get_content_type()
        assert isinstance(content_type, str)
        assert "text" in content_type.lower() or "openmetrics" in content_type.lower()
