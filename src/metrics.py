# -*- coding: utf-8 -*-
"""Prometheus metrics for EntroFeed."""

from dataclasses import dataclass
from typing import Optional

from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Token usage metrics
TOKEN_USAGE_TOTAL = Counter(
    "entrofeed_token_usage_total",
    "Total token usage",
    ["model", "type"]  # labels: input, output
)

LLM_REQUESTS_TOTAL = Counter(
    "entrofeed_llm_requests_total",
    "Total LLM API requests",
    ["provider", "model", "status"]  # labels: success, error
)

LLM_REQUEST_DURATION = Histogram(
    "entrofeed_llm_request_duration_seconds",
    "LLM request duration",
    ["provider", "model"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

# Cost tracking metrics
LLM_COST_USD = Counter(
    "entrofeed_llm_cost_usd",
    "Estimated LLM cost in USD",
    ["provider", "model"]
)

# Feed metrics
FEED_COUNT = Gauge(
    "entrofeed_feed_count",
    "Number of configured feeds"
)

FEED_ENTRY_COUNT = Gauge(
    "entrofeed_feed_entry_count",
    "Number of entries per feed",
    ["feed_id"]
)

FEED_REFRESH_DURATION = Histogram(
    "entrofeed_feed_refresh_duration_seconds",
    "Feed refresh duration",
    ["feed_id"],
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)
)

# Recommendation metrics
RECOMMENDATION_REQUESTS = Counter(
    "entrofeed_recommendation_requests_total",
    "Total recommendation requests",
    ["type"]  # labels: interest, trending, similar
)

# Plugin lifecycle metrics
PLUGIN_STATUS = Gauge(
    "entrofeed_plugin_status",
    "Plugin health status (1=healthy, 0=unhealthy, -1=unknown)",
    ["plugin_type", "plugin_id"]
)

PLUGIN_INIT_DURATION = Histogram(
    "entrofeed_plugin_init_duration_seconds",
    "Plugin initialization duration",
    ["plugin_type", "plugin_id"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5)
)

PLUGIN_OPERATIONS = Counter(
    "entrofeed_plugin_operations_total",
    "Plugin operations counter",
    ["plugin_type", "plugin_id", "operation"]  # operation: init, shutdown, check, error
)


# Pricing lookup for cost estimation (价格估算)
LLM_PRICING = {
    # Provider: {Model: (input_cost_per_1k, output_cost_per_1k)}
    "deepseek": {
        "deepseek-chat": (0.001, 0.001),  # $0.001/1K tokens
    },
    "zhipu": {
        "glm-4": (0.0001, 0.0001),  # ¥0.1/1K tokens ~= $0.00014
    },
    "moonshot": {
        "moonshot-v1-128k": (0.000012, 0.000012),  # ¥0.012/1K tokens
    },
    "dashscope": {
        "qwen-plus": (0.000004, 0.000004),  # ¥0.004/1K tokens
        "qwen-max": (0.00012, 0.00012),  # ¥0.12/1K tokens
    },
    "openai": {
        "gpt-4o-mini": (0.00015, 0.0006),  # $0.15/1M input, $0.6/1M output
        "gpt-4o": (0.0025, 0.01),  # $2.5/1M input, $10/1M output
    },
}


@dataclass
class PluginCheckResult:
    """Result of plugin availability check."""
    available: bool
    reason: Optional[str] = None
    missing_env: Optional[list[str]] = None

    def __post_init__(self):
        if self.missing_env is None:
            self.missing_env = []


def record_token_usage(model: str, input_tokens: int, output_tokens: int):
    """Record token usage metrics."""
    TOKEN_USAGE_TOTAL.labels(model=model, type="input").inc(input_tokens)
    TOKEN_USAGE_TOTAL.labels(model=model, type="output").inc(output_tokens)


def record_llm_request(provider: str, model: str, success: bool, duration: float):
    """Record LLM request metrics."""
    status = "success" if success else "error"
    LLM_REQUESTS_TOTAL.labels(provider=provider, model=model, status=status).inc()
    LLM_REQUEST_DURATION.labels(provider=provider, model=model).observe(duration)


def record_llm_cost(provider: str, model: str, input_tokens: int, output_tokens: int):
    """Record LLM cost in USD based on token usage.

    Args:
        provider: LLM provider ID (e.g., 'deepseek', 'dashscope')
        model: Model name (e.g., 'deepseek-chat', 'qwen-plus')
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
    """
    if provider in LLM_PRICING and model in LLM_PRICING[provider]:
        input_cost, output_cost = LLM_PRICING[provider][model]
        total_cost = (input_tokens * input_cost + output_tokens * output_cost) / 1000
        LLM_COST_USD.labels(provider=provider, model=model).inc(total_cost)


def record_plugin_init(plugin_type: str, plugin_id: str, duration: float, success: bool):
    """Record plugin initialization."""
    PLUGIN_OPERATIONS.labels(plugin_type=plugin_type, plugin_id=plugin_id, operation="init").inc()
    PLUGIN_INIT_DURATION.labels(plugin_type=plugin_type, plugin_id=plugin_id).observe(duration)
    PLUGIN_STATUS.labels(plugin_type=plugin_type, plugin_id=plugin_id).set(1 if success else 0)


def record_plugin_shutdown(plugin_type: str, plugin_id: str):
    """Record plugin shutdown."""
    PLUGIN_OPERATIONS.labels(plugin_type=plugin_type, plugin_id=plugin_id, operation="shutdown").inc()
    PLUGIN_STATUS.labels(plugin_type=plugin_type, plugin_id=plugin_id).set(-1)


def record_plugin_check(plugin_type: str, plugin_id: str, available: bool, reason: Optional[str] = None):
    """Record plugin health check result."""
    PLUGIN_OPERATIONS.labels(plugin_type=plugin_type, plugin_id=plugin_id, operation="check").inc()
    PLUGIN_STATUS.labels(plugin_type=plugin_type, plugin_id=plugin_id).set(1 if available else 0)


def record_plugin_error(plugin_type: str, plugin_id: str):
    """Record plugin error."""
    PLUGIN_OPERATIONS.labels(plugin_type=plugin_type, plugin_id=plugin_id, operation="error").inc()


def get_metrics():
    """Generate metrics output for Prometheus."""
    return generate_latest()


def get_content_type():
    """Get Prometheus content type."""
    return CONTENT_TYPE_LATEST
