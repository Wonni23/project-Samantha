# app/integrations/voice/__init__.py
"""
Voice Integration 모듈

TTS Provider 인터페이스 및 구현체 제공.
get_tts_provider()로 config 기반 Provider 싱글톤 반환.
"""
import logging
from typing import Optional

from app.integrations.voice.base import BaseTTSProvider, TTSConfig, TTSResult

logger = logging.getLogger(__name__)

_provider_instance: Optional[BaseTTSProvider] = None


def get_tts_provider() -> BaseTTSProvider:
    """TTS Provider 싱글톤 반환 (settings.TTS_PROVIDER 기반 분기)

    Returns:
        BaseTTSProvider 구현체 (OpenAI 또는 Google)
    """
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    from app.core.config import settings

    provider_name = settings.TTS_PROVIDER.lower()

    if provider_name == "openai":
        from app.integrations.voice.openai_tts import OpenAITTSProvider
        _provider_instance = OpenAITTSProvider()
    elif provider_name == "google":
        from app.integrations.voice.google_tts import GoogleTTSProvider
        _provider_instance = GoogleTTSProvider()
    else:
        logger.warning("Unknown TTS_PROVIDER '%s', falling back to OpenAI", provider_name)
        from app.integrations.voice.openai_tts import OpenAITTSProvider
        _provider_instance = OpenAITTSProvider()

    logger.info("TTS Provider initialized: %s", type(_provider_instance).__name__)
    return _provider_instance


__all__ = [
    "BaseTTSProvider",
    "TTSConfig",
    "TTSResult",
    "get_tts_provider",
]
