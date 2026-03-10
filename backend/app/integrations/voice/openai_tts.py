# app/integrations/voice/openai_tts.py
"""
OpenAI TTS Provider 구현

OpenAI TTS-1 모델 사용, LRU 캐시 + 재시도 로직 포함.
Provider는 전달받은 speaking_rate를 그대로 사용한다.
"""
import asyncio
import logging
from collections import OrderedDict
from typing import AsyncIterator, Optional

from openai import AsyncOpenAI, APIError, RateLimitError, APIConnectionError, APITimeoutError

from app.core.config import settings
from app.core.exceptions import TTSException
from app.integrations.voice.base import BaseTTSProvider, TTSConfig, TTSResult

# MP3: 프레임 기반이라 세그먼트별 독립 합성 결과를 단순 concat해도 유효한 파일 유지.
# opus(OGG 컨테이너)는 다중 세그먼트 concat 시 깨지므로 MP3 사용.
_RESPONSE_FORMAT = "mp3"
_AUDIO_ENCODING = "mp3"

logger = logging.getLogger(__name__)

# LRU 캐시 상한 (~10KB/항목 × 256 ≈ 2.5MB)
_MAX_CACHE_SIZE = 256


class OpenAITTSProvider(BaseTTSProvider):
    """OpenAI TTS Provider

    voice options: alloy, echo, fable, onyx, nova, shimmer
    """

    def __init__(self, api_key: Optional[str] = None):
        self._client = AsyncOpenAI(api_key=api_key or settings.OPENAI_API_KEY)
        self._cache: OrderedDict[tuple, bytes] = OrderedDict()

    @property
    def supports_streaming(self) -> bool:
        return True

    @property
    def default_voice(self) -> str:
        return settings.TTS_DEFAULT_VOICE

    async def synthesize(
        self,
        text: str,
        config: Optional[TTSConfig] = None,
    ) -> TTSResult:
        """텍스트를 오디오로 합성 (캐시 + 재시도)

        Args:
            text: 합성할 텍스트
            config: 합성 설정 (voice, speaking_rate 등)

        Returns:
            TTSResult: MP3 오디오 데이터

        Raises:
            TTSException: 3회 재시도 후에도 실패 시
        """
        cfg = config or TTSConfig()
        voice = cfg.voice or self.default_voice
        speed = cfg.speaking_rate

        # 캐시 확인
        cache_key = (text, voice, speed)
        if cache_key in self._cache:
            self._cache.move_to_end(cache_key)
            return TTSResult(
                audio_content=self._cache[cache_key],
                audio_encoding=_AUDIO_ENCODING,
            )

        # API 호출 (재시도)
        audio_bytes = await self._call_with_retry(text, voice, speed)

        # 캐시 저장
        self._cache[cache_key] = audio_bytes
        if len(self._cache) > _MAX_CACHE_SIZE:
            self._cache.popitem(last=False)

        return TTSResult(
            audio_content=audio_bytes,
            audio_encoding=_AUDIO_ENCODING,
        )

    async def synthesize_streaming(
        self,
        text: str,
        config: Optional[TTSConfig] = None,
        chunk_size: int = 4096,
    ) -> "AsyncIterator[bytes]":
        """네이티브 스트리밍 합성 — 첫 오디오 청크를 즉시 yield

        OpenAI with_streaming_response를 사용하여 서버가 오디오를
        생성하는 즉시 청크를 전달받습니다. 전체 합성 대기 대비
        첫 오디오 바이트가 ~500-800ms 빠릅니다.
        """
        cfg = config or TTSConfig()
        voice = cfg.voice or self.default_voice
        speed = cfg.speaking_rate

        async with self._client.audio.speech.with_streaming_response.create(
            model="tts-1",
            voice=voice,
            input=text,
            speed=speed,
            response_format=_RESPONSE_FORMAT,
        ) as response:
            async for chunk in response.iter_bytes(chunk_size):
                yield chunk

    async def _call_with_retry(
        self, text: str, voice: str, speed: float
    ) -> bytes:
        """OpenAI TTS API 호출 (3회 재시도, 지수 백오프)"""
        max_retries = 3
        backoff_base = 0.5

        for attempt in range(max_retries):
            try:
                response = await self._client.audio.speech.create(
                    model="tts-1",
                    voice=voice,
                    input=text,
                    speed=speed,
                    response_format=_RESPONSE_FORMAT,
                )
                return response.content

            except asyncio.CancelledError:
                raise

            except (APIError, RateLimitError, APIConnectionError, APITimeoutError) as e:
                logger.warning(
                    "[TTS] API error attempt %d/%d: %s",
                    attempt + 1, max_retries, e,
                    extra={"text_length": len(text), "voice": voice},
                )
                if attempt == max_retries - 1:
                    raise TTSException(
                        f"TTS 변환 실패 (3회 재시도 후): {type(e).__name__}"
                    ) from e
                await asyncio.sleep(backoff_base * (2 ** attempt))

        raise TTSException("TTS 변환 실패: 예기치 않은 상태")
