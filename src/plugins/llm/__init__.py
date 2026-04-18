# -*- coding: utf-8 -*-
"""LLM Plugin module - Model wrapper base and registry for EntroFeed."""

import os
import time
from abc import abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar, Dict, List, Optional, Type

from pydantic import BaseModel

from src.kernel.registry import PluginBase, PluginRegistry
from src.metrics import record_llm_request, record_token_usage
from src.models.feed import Feed, FeedEntry


class ModelCapability(str, Enum):
    """Model capability flags."""
    TEXT = "text"                    # Text generation
    REASONING = "reasoning"          # Chain-of-thought reasoning
    VISION = "vision"                # Image understanding
    IMAGE_GENERATION = "image_gen"   # Image generation
    FUNCTION_CALLING = "func_call"   # Function/tool calling
    CODE = "code"                    # Code generation
    LONG_CONTEXT = "long_ctx"        # Long context support


class ModelInfo(BaseModel):
    """Information about a specific model."""
    name: str
    display_name: str
    provider: str
    capabilities: List[ModelCapability]
    max_tokens: int = 8192
    description: str = ""
    context_window: int = 0  # 0 means unknown
    pricing_hint: str = ""   # e.g., "$0.001/1K tokens"


@dataclass
class ModelCatalog:
    """Catalog of all available models with their capabilities."""
    
    # DeepSeek models
    deepseek_chat: ModelInfo = field(default_factory=lambda: ModelInfo(
        name="deepseek-chat",
        display_name="DeepSeek V3",
        provider="deepseek",
        capabilities=[ModelCapability.TEXT, ModelCapability.REASONING, ModelCapability.CODE, ModelCapability.FUNCTION_CALLING],
        max_tokens=64000,
        context_window=128000,
        description="DeepSeek's latest flagship model with strong reasoning and coding abilities",
        pricing_hint="$0.001/1K tokens"
    ))
    
    deepseek_coder: ModelInfo = field(default_factory=lambda: ModelInfo(
        name="deepseek-coder",
        display_name="DeepSeek Coder",
        provider="deepseek",
        capabilities=[ModelCapability.TEXT, ModelCapability.CODE],
        max_tokens=16000,
        context_window=128000,
        description="Specialized code generation model",
        pricing_hint="$0.001/1K tokens"
    ))
    
    # Zhipu AI (智谱AI) models
    glm4: ModelInfo = field(default_factory=lambda: ModelInfo(
        name="glm-4",
        display_name="GLM-4",
        provider="zhipu",
        capabilities=[ModelCapability.TEXT, ModelCapability.REASONING, ModelCapability.FUNCTION_CALLING],
        max_tokens=128000,
        context_window=128000,
        description="Zhipu's latest flagship model",
        pricing_hint="¥0.1/1K tokens"
    ))
    
    glm4v: ModelInfo = field(default_factory=lambda: ModelInfo(
        name="glm-4v",
        display_name="GLM-4V",
        provider="zhipu",
        capabilities=[ModelCapability.TEXT, ModelCapability.VISION, ModelCapability.FUNCTION_CALLING],
        max_tokens=8000,
        context_window=128000,
        description="Zhipu's vision model with image understanding",
        pricing_hint="¥0.5/1K tokens"
    ))
    
    # Baichuan (百川) models
    baichuan4: ModelInfo = field(default_factory=lambda: ModelInfo(
        name="Baichuan4",
        display_name="百川4",
        provider="baichuan",
        capabilities=[ModelCapability.TEXT, ModelCapability.REASONING],
        max_tokens=8000,
        context_window=128000,
        description="Baichuan's latest large language model",
        pricing_hint="¥0.08/1K tokens"
    ))
    
    # Moonshot (月之暗面/Kimi) models
    moonshot_v1: ModelInfo = field(default_factory=lambda: ModelInfo(
        name="moonshot-v1-128k",
        display_name="Kimi 128K",
        provider="moonshot",
        capabilities=[ModelCapability.TEXT, ModelCapability.REASONING, ModelCapability.LONG_CONTEXT],
        max_tokens=96000,
        context_window=128000,
        description="Moonshot's Kimi with 128K context window",
        pricing_hint="¥0.012/1K tokens"
    ))
    
    moonshot_v1_32k: ModelInfo = field(default_factory=lambda: ModelInfo(
        name="moonshot-v1-32k",
        display_name="Kimi 32K",
        provider="moonshot",
        capabilities=[ModelCapability.TEXT, ModelCapability.REASONING],
        max_tokens=24000,
        context_window=32000,
        description="Moonshot's Kimi with 32K context window",
        pricing_hint="¥0.006/1K tokens"
    ))
    
    # Tencent Hunyuan (腾讯混元) models
    hunyuan_pro: ModelInfo = field(default_factory=lambda: ModelInfo(
        name="hunyuan-pro",
        display_name="混元Pro",
        provider="tencent",
        capabilities=[ModelCapability.TEXT, ModelCapability.REASONING, ModelCapability.FUNCTION_CALLING],
        max_tokens=8000,
        context_window=128000,
        description="Tencent's Hunyuan Pro model",
        pricing_hint="¥0.05/1K tokens"
    ))
    
    hunyuan_vision: ModelInfo = field(default_factory=lambda: ModelInfo(
        name="hunyuan-vision",
        display_name="混元视觉",
        provider="tencent",
        capabilities=[ModelCapability.TEXT, ModelCapability.VISION, ModelCapability.FUNCTION_CALLING],
        max_tokens=8000,
        context_window=128000,
        description="Tencent's Hunyuan vision model",
        pricing_hint="¥0.1/1K tokens"
    ))
    
    # ByteDance Doubao (字节豆包) models
    doubao_pro: ModelInfo = field(default_factory=lambda: ModelInfo(
        name="Doubao-pro-32k",
        display_name="豆包Pro 32K",
        provider="bytedance",
        capabilities=[ModelCapability.TEXT, ModelCapability.REASONING],
        max_tokens=24000,
        context_window=32000,
        description="ByteDance's Doubao Pro model",
        pricing_hint="¥0.003/1K tokens"
    ))
    
    doubao_vision: ModelInfo = field(default_factory=lambda: ModelInfo(
        name="Doubao-vision",
        display_name="豆包视觉",
        provider="bytedance",
        capabilities=[ModelCapability.TEXT, ModelCapability.VISION],
        max_tokens=8000,
        context_window=32000,
        description="ByteDance's Doubao vision model",
        pricing_hint="¥0.005/1K tokens"
    ))
    
    # OpenAI models (existing)
    gpt4o: ModelInfo = field(default_factory=lambda: ModelInfo(
        name="gpt-4o",
        display_name="GPT-4o",
        provider="openai",
        capabilities=[ModelCapability.TEXT, ModelCapability.VISION, ModelCapability.FUNCTION_CALLING, ModelCapability.CODE],
        max_tokens=128000,
        context_window=128000,
        description="OpenAI's latest flagship model with vision",
        pricing_hint="$0.015/1K tokens"
    ))
    
    gpt4o_mini: ModelInfo = field(default_factory=lambda: ModelInfo(
        name="gpt-4o-mini",
        display_name="GPT-4o Mini",
        provider="openai",
        capabilities=[ModelCapability.TEXT, ModelCapability.VISION, ModelCapability.FUNCTION_CALLING],
        max_tokens=128000,
        context_window=128000,
        description="OpenAI's cost-effective mini model",
        pricing_hint="$0.0015/1K tokens"
    ))
    
    # Qwen models (阿里通义)
    qwen_plus: ModelInfo = field(default_factory=lambda: ModelInfo(
        name="qwen-plus",
        display_name="通义千问Plus",
        provider="dashscope",
        capabilities=[ModelCapability.TEXT, ModelCapability.REASONING, ModelCapability.CODE, ModelCapability.FUNCTION_CALLING],
        max_tokens=8000,
        context_window=131072,
        description="Alibaba's Qwen Plus model",
        pricing_hint="¥0.004/1K tokens"
    ))
    
    qwen_max: ModelInfo = field(default_factory=lambda: ModelInfo(
        name="qwen-max",
        display_name="通义千问Max",
        provider="dashscope",
        capabilities=[ModelCapability.TEXT, ModelCapability.REASONING, ModelCapability.CODE, ModelCapability.FUNCTION_CALLING],
        max_tokens=8000,
        context_window=131072,
        description="Alibaba's Qwen Max model",
        pricing_hint="¥0.12/1K tokens"
    ))
    
    qwen_vl_max: ModelInfo = field(default_factory=lambda: ModelInfo(
        name="qwen-vl-max",
        display_name="通义千问视觉",
        provider="dashscope",
        capabilities=[ModelCapability.TEXT, ModelCapability.VISION, ModelCapability.FUNCTION_CALLING],
        max_tokens=8000,
        context_window=131072,
        description="Alibaba's Qwen Vision model",
        pricing_hint="¥0.02/1K tokens"
    ))

    def get_all_models(self) -> List[ModelInfo]:
        """Get all models as a list."""
        return [
            self.deepseek_chat, self.deepseek_coder,
            self.glm4, self.glm4v,
            self.baichuan4,
            self.moonshot_v1, self.moonshot_v1_32k,
            self.hunyuan_pro, self.hunyuan_vision,
            self.doubao_pro, self.doubao_vision,
            self.gpt4o, self.gpt4o_mini,
            self.qwen_plus, self.qwen_max, self.qwen_vl_max,
        ]
    
    def get_model_info(self, provider: str, model_name: str) -> Optional[ModelInfo]:
        """Get model info by provider and model name."""
        for model in self.get_all_models():
            if model.provider == provider and model.name == model_name:
                return model
        return None
    
    def get_models_by_provider(self, provider: str) -> List[ModelInfo]:
        """Get all models for a specific provider."""
        return [m for m in self.get_all_models() if m.provider == provider]
    
    def get_models_by_capability(self, capability: ModelCapability) -> List[ModelInfo]:
        """Get all models with a specific capability."""
        return [m for m in self.get_all_models() if capability in m.capabilities]
    
    def get_text_models(self) -> List[ModelInfo]:
        """Get all text generation models."""
        return self.get_models_by_capability(ModelCapability.TEXT)
    
    def get_vision_models(self) -> List[ModelInfo]:
        """Get all vision models."""
        return self.get_models_by_capability(ModelCapability.VISION)
    
    def get_reasoning_models(self) -> List[ModelInfo]:
        """Get all reasoning models."""
        return self.get_models_by_capability(ModelCapability.REASONING)


# Global model catalog instance
MODEL_CATALOG = ModelCatalog()


class ModelWrapperBase(PluginBase):
    """Base class for all LLM providers."""

    id: ClassVar[str] = "base_llm"

    @classmethod
    def get_plugin_type(cls) -> str:
        """Return the plugin type string."""
        return "llm"

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        pass

    @abstractmethod
    def summarize(self, feed: Feed, entry: FeedEntry, mk: str) -> str:
        pass

    def _make_chat_call(self, system: str, prompt: str, **kwargs) -> str:
        return self.chat([
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ], **kwargs)

    def chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        **kwargs
    ) -> Dict[str, Any]:
        """Chat with function calling support.

        Args:
            messages: List of message dicts with role and content
            tools: List of tool definitions in OpenAI format
            **kwargs: Additional arguments

        Returns:
            Dict with 'content' (str) and optionally 'tool_calls' list
        """
        raise NotImplementedError("Subclass must implement chat_with_tools")

    def get_summarization_prompt(self, mk: str) -> str:
        return f"Summarize this article:\n\n{mk}"

    @property
    def summarization_system_prompt(self) -> str:
        return """Your goal is to write a brief but detailed summary of the text given to you.
Only output the summary without any headings or sections.
Provide the summary in markdown."""

    def _record_metrics(self, input_tokens: int = 0, output_tokens: int = 0, success: bool = True):
        """Record metrics for this LLM call."""
        if input_tokens > 0 or output_tokens > 0:
            record_token_usage(self.model, input_tokens, output_tokens)
        
        start_time = getattr(self, "_last_call_start", None)
        duration = time.time() - start_time if start_time else 0
        record_llm_request(self.id, self.model, success, duration)

    def _start_call(self):
        """Mark the start of an LLM call for timing."""
        self._last_call_start = time.time()

    @property
    def model_info(self) -> Optional[ModelInfo]:
        """Get the model info for this handler."""
        return MODEL_CATALOG.get_model_info(self.id, self.model)
    
    @property
    def capabilities(self) -> List[ModelCapability]:
        """Get the capabilities of this model."""
        info = self.model_info
        return list(info.capabilities) if info else []
    
    def supports_vision(self) -> bool:
        """Check if this model supports vision."""
        return ModelCapability.VISION in self.capabilities
    
    def supports_function_calling(self) -> bool:
        """Check if this model supports function calling."""
        return ModelCapability.FUNCTION_CALLING in self.capabilities


class LLMPluginRegistry:
    """Registry for LLM plugins with auto-registration."""

    _handlers: Dict[str, Type[ModelWrapperBase]] = {}
    _provider_defaults: Dict[str, Dict[str, Any]] = {
        # DeepSeek
        "deepseek": {
            "model": "deepseek-chat",
            "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
            "base_url": "https://api.deepseek.com/v1",
        },
        # Zhipu AI (智谱)
        "zhipu": {
            "model": "glm-4",
            "api_key": os.getenv("ZHIPU_API_KEY", ""),
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
        },
        # Baichuan (百川)
        "baichuan": {
            "model": "Baichuan4",
            "api_key": os.getenv("BAICHUAN_API_KEY", ""),
            "base_url": "https://api.baichuan-ai.com/v1",
        },
        # Moonshot (月之暗面/Kimi)
        "moonshot": {
            "model": "moonshot-v1-128k",
            "api_key": os.getenv("MOONSHOT_API_KEY", ""),
            "base_url": "https://api.moonshot.cn/v1",
        },
        # Tencent Hunyuan (腾讯混元)
        "tencent": {
            "model": "hunyuan-pro",
            "secret_id": os.getenv("TENCENT_SECRET_ID", ""),
            "secret_key": os.getenv("TENCENT_SECRET_KEY", ""),
        },
        # ByteDance Doubao (字节豆包)
        "bytedance": {
            "model": "Doubao-pro-32k",
            "api_key": os.getenv("BYTEDANCE_API_KEY", ""),
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        },
        # Dashscope (阿里云)
        "dashscope": {
            "model": "qwen-plus",
            "api_key": os.getenv("DASHSCOPE_API_KEY"),
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "temperature": 0.2,
            "max_tokens": 4000,
        },
        # Ollama (local)
        "ollama": {
            "model": os.getenv("OLLAMA_MODEL", "llama3"),
            "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            "options": {"temperature": 0.2},
        },
        # OpenAI
        "openai": {
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "api_key": os.getenv("OPENAI_API_KEY", ""),
        },
    }
    _provider_aliases: Dict[str, str] = {
        "dummy": "dummy_llm",
        "null": "null_llm",
        "qwen": "dashscope",  # Alias for dashscope
        "aliyun": "dashscope",
    }

    @classmethod
    def register(cls, handler_cls: Type[ModelWrapperBase]) -> None:
        cls._handlers[handler_cls.id] = handler_cls
        PluginRegistry.register("llm", handler_cls)

    @classmethod
    def get_handler(cls, handler_id: str) -> Optional[Type[ModelWrapperBase]]:
        return cls._handlers.get(handler_id)

    @classmethod
    def list_handlers(cls) -> List[str]:
        return list(cls._handlers.keys())

    @classmethod
    def create(
        cls,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> ModelWrapperBase:
        provider = provider or os.getenv("DEFAULT_LLM_PROVIDER", "dashscope")
        
        # Resolve aliases
        handler_id = cls._provider_aliases.get(provider, provider)
        handler_cls = cls._handlers.get(handler_id)
        
        if not handler_cls:
            raise ValueError(f"Unknown LLM provider: {provider}")

        defaults = cls._provider_defaults.get(handler_id, {})
        config = {**defaults, **kwargs}
        if model:
            config["model"] = model

        return handler_cls(**config)
    
    @classmethod
    def get_available_providers(cls) -> List[Dict[str, Any]]:
        """Get list of available providers with their status."""
        providers = []
        for provider_id in cls.list_handlers():
            handler_cls = cls.get_handler(provider_id)
            if handler_cls:
                # Check if required env vars are set
                required_env = getattr(handler_cls, "required_env", [])
                missing_env = [e for e in required_env if not os.getenv(e)]
                models = MODEL_CATALOG.get_models_by_provider(provider_id)
                providers.append({
                    "id": provider_id,
                    "name": _get_provider_display_name(provider_id),
                    "available": len(missing_env) == 0,
                    "missing_env": missing_env,
                    "models": [{"name": m.name, "display_name": m.display_name} for m in models],
                })
        return providers


def _get_provider_display_name(provider_id: str) -> str:
    """Get display name for a provider."""
    names = {
        "deepseek": "DeepSeek",
        "zhipu": "智谱AI (GLM)",
        "baichuan": "百川智能",
        "moonshot": "月之暗面 (Kimi)",
        "tencent": "腾讯混元",
        "bytedance": "字节豆包",
        "dashscope": "阿里云通义",
        "openai": "OpenAI",
        "ollama": "Ollama (本地)",
        "dummy_llm": "Dummy (测试)",
        "null_llm": "Null (无LLM)",
    }
    return names.get(provider_id, provider_id)


def create_llm_handler(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs
) -> ModelWrapperBase:
    return LLMPluginRegistry.create(provider=provider, model=model, **kwargs)


def get_default_provider() -> str:
    return os.getenv("DEFAULT_LLM_PROVIDER", "dashscope")


def get_model_catalog() -> ModelCatalog:
    """Get the global model catalog."""
    return MODEL_CATALOG


def get_all_models() -> List[ModelInfo]:
    """Get all available models."""
    return MODEL_CATALOG.get_all_models()


def get_provider_models(provider: str) -> List[ModelInfo]:
    """Get models for a specific provider."""
    return MODEL_CATALOG.get_models_by_provider(provider)


# Import all plugins to trigger auto-registration
from src.plugins.llm import openai, ollama, dashscope, deepseek, zhipu, baichuan, moonshot, tencent, bytedance, dummy, null


__all__ = [
    "ModelWrapperBase",
    "LLMPluginRegistry",
    "create_llm_handler",
    "get_default_provider",
    "ModelCapability",
    "ModelInfo",
    "ModelCatalog",
    "MODEL_CATALOG",
    "get_model_catalog",
    "get_all_models",
    "get_provider_models",
]
