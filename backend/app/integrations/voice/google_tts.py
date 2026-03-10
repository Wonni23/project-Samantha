# app/integrations/voice/google_tts.py
"""
Google Cloud TTS Provider 구현

Chirp3-HD 음성 지원, 한국어 SSML 최적화 포함.
Provider는 전달받은 speaking_rate를 사용한다.
"""

import base64
import logging
import re
from typing import Optional

import httpx

from app.core.config import settings
from app.core.exceptions import TTSException
from app.integrations.voice.base import BaseTTSProvider, TTSConfig, TTSResult

logger = logging.getLogger(__name__)


def text_to_ssml(text: str, rate: float = 1.0) -> str:
    """일반 텍스트를 SSML로 변환

    Args:
        text: 변환할 텍스트
        rate: 말하기 속도 (0.25 ~ 4.0)

    Returns:
        SSML 형식 문자열

    Raises:
        ValueError: text가 빈 문자열이거나 공백만 포함

    SSML 최적화:
    - 감정 표현 (ㅎㅎ, ㅠㅠ) → <sub>
    - 쉼표 → 자연스러운 휴지
    - 접속사 뒤 휴지 추가
    - "..." → 긴 휴지
    """
    if not text or not text.strip():
        raise ValueError("text는 비어 있을 수 없습니다")

    # 1. 웃음 표현
    text = re.sub(r'(ㅎ{2,})', r'<sub alias="웃음">\1</sub>', text)
    text = re.sub(r'(ㅋ{2,})', r'<sub alias="웃음">\1</sub>', text)
    text = re.sub(r'(ㅍ{2,})', r'<sub alias="웃음">\1</sub>', text)

    # 2. 울음 표현
    text = re.sub(r'(ㅠ{2,})', r'<sub alias="흐느낌">\1</sub>', text)
    text = re.sub(r'(ㅜ{2,})', r'<sub alias="흐느낌">\1</sub>', text)

    # 3. 쉼표 뒤 짧은 휴지
    text = text.replace(',', ',<break time="300ms"/>')

    # 4. 접속사/연결어 뒤 휴지 추가 (자연스러운 호흡)
    connectors = ['그래서', '그런데', '하지만', '그리고', '그러니까', '근데']
    for conn in connectors:
        text = text.replace(f'{conn} ', f'{conn}<break time="250ms"/> ')

    # 5. "..." 처리 (긴 휴지)
    text = re.sub(r'\.{3,}', '<break time="500ms"/>', text)

    return f'<speak><prosody rate="{rate}">{text}</prosody></speak>'


class GoogleTTSProvider(BaseTTSProvider):
    """Google Cloud TTS Provider

    Chirp3-HD 음성 지원
    """

    ENDPOINT = "https://texttospeech.googleapis.com/v1/text:synthesize"

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: Google API 키 (None이면 settings에서 로드)
        """
        self._api_key = api_key or settings.GOOGLE_TTS_API_KEY or settings.GEMINI_API_KEY

    @property
    def supports_streaming(self) -> bool:
        """Google TTS는 네이티브 스트리밍 미지원"""
        return False

    @property
    def default_voice(self) -> str:
        """기본 음성: Chirp3-HD Leda (여성)"""
        return settings.TTS_DEFAULT_VOICE

    async def synthesize(
        self,
        text: str,
        config: Optional[TTSConfig] = None
    ) -> TTSResult:
        """텍스트를 오디오로 합성

        Args:
            text: 합성할 텍스트
            config: 합성 설정

        Returns:
            TTSResult: MP3 오디오 데이터

        Raises:
            TTSException: API 호출 실패 시
        """
        cfg = config or TTSConfig()

        # 음성 결정 (config > default)
        voice = cfg.voice or self.default_voice

        # 속도 결정 (config > 환경변수)
        speaking_rate = cfg.speaking_rate
        if cfg.speaking_rate == 1.0:  # 기본값이면 환경변수 확인
            speaking_rate = settings.TTS_DEFAULT_SPEED

        # SSML 변환
        ssml_text = text_to_ssml(text, speaking_rate)

        audio_config = {
            "audioEncoding": cfg.audio_encoding,
            "speakingRate": speaking_rate,
        }

        payload = {
            "input": {"ssml": ssml_text},
            "voice": {
                "languageCode": cfg.language_code,
                "name": voice
            },
            "audioConfig": audio_config,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.ENDPOINT,
                headers={"x-goog-api-key": self._api_key},
                json=payload,
                timeout=30.0
            )

            if response.status_code != 200:
                logger.error(
                    "Google TTS API 실패: status=%d, response=%s",
                    response.status_code, response.text,
                )
                raise TTSException(
                    f"Google TTS API 오류 (HTTP {response.status_code})"
                )

            result = response.json()
            audio_content = base64.b64decode(result["audioContent"])

            logger.debug(
                "Google TTS 합성 완료: %d bytes, text=%s",
                len(audio_content), text[:50],
            )

            return TTSResult(
                audio_content=audio_content,
                audio_encoding=cfg.audio_encoding
            )
