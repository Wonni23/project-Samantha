# app/integrations/voice/base.py
"""
TTS(Text-to-Speech) 공통 인터페이스 정의

LLM Provider와 동일한 ABC 패턴 적용
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, AsyncIterator


@dataclass
class TTSConfig:
    """TTS 합성 설정

    speaking_rate는 기본값(1.0) 또는 호출자 전달값을 사용한다.
    Provider는 전달된 speaking_rate를 보정/소비한다.
    """
    voice: Optional[str] = None  # None이면 Provider의 default_voice 사용
    language_code: str = "ko-KR"
    speaking_rate: float = 1.0  # 0.25 ~ 4.0
    audio_encoding: str = "MP3"  # MP3, LINEAR16, OGG_OPUS

    def __post_init__(self):
        self.speaking_rate = max(0.25, min(4.0, self.speaking_rate))


@dataclass
class TTSResult:
    """TTS 합성 결과"""
    audio_content: bytes  # 오디오 바이너리 데이터
    audio_encoding: str  # 사용된 인코딩 형식
    duration_ms: Optional[int] = None  # 오디오 길이 (밀리초, 일부 Provider만 제공)


class BaseTTSProvider(ABC):
    """TTS Provider 기본 인터페이스

    모든 TTS Provider는 이 클래스를 상속받아 구현
    """

    @property
    @abstractmethod
    def supports_streaming(self) -> bool:
        """스트리밍 합성 지원 여부

        Returns:
            True면 네이티브 스트리밍, False면 fallback 청크 분할
        """
        pass

    @property
    @abstractmethod
    def default_voice(self) -> str:
        """기본 음성 ID

        TTSConfig.voice가 None일 때 사용
        """
        pass

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        config: Optional[TTSConfig] = None
    ) -> TTSResult:
        """텍스트를 오디오로 합성

        Args:
            text: 합성할 텍스트
            config: 합성 설정 (None이면 기본값 사용)

        Returns:
            TTSResult: 오디오 데이터와 메타정보
        """
        pass

    async def synthesize_streaming(
        self,
        text: str,
        config: Optional[TTSConfig] = None,
        chunk_size: int = 4096
    ) -> AsyncIterator[bytes]:
        """텍스트를 오디오로 스트리밍 합성

        기본 구현: 전체 합성 후 청크 분할 (fallback)
        네이티브 스트리밍 지원 Provider는 오버라이드

        Args:
            text: 합성할 텍스트
            config: 합성 설정
            chunk_size: 청크 크기 (바이트)

        Yields:
            bytes: 오디오 청크
        """
        result = await self.synthesize(text, config)
        for i in range(0, len(result.audio_content), chunk_size):
            yield result.audio_content[i:i + chunk_size]
