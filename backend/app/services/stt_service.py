# app/services/stt_service.py
import asyncio
import io
import logging
import re
from dataclasses import dataclass
from typing import List

from openai import AsyncOpenAI, APIError, RateLimitError, APIConnectionError, APITimeoutError
from app.core.config import settings
from app.core.exceptions import STTException

logger = logging.getLogger(__name__)


# ==================== TranscriptionResult ====================


@dataclass(frozen=True)
class TranscriptionResult:
    """STT 변환 결과 (불변 객체)

    Attributes:
        text: 변환된 텍스트
        is_hallucination: 할루시네이션 판별 결과
        avg_no_speech_prob: 세그먼트 평균 no_speech_prob
        avg_logprob: 세그먼트 평균 avg_logprob
        segment_count: 세그먼트 개수
    """
    text: str
    is_hallucination: bool
    avg_no_speech_prob: float
    avg_logprob: float
    segment_count: int


# ==================== Hallucination Patterns ====================


HALLUCINATION_PATTERNS: List[re.Pattern] = [
    re.compile(r"시청해\s*주셔서\s*감사"),
    re.compile(r"구독과?\s*좋아요"),
    re.compile(r"(?:^|\s)(?:MBC|SBS|KBS|JTBC|YTN|TV조선|채널A)(?:\s|$)"),
    re.compile(r"^(네\s*){3,}$"),
    re.compile(r"(감사합니다\s*){2,}"),
    re.compile(r"(안녕하세요\s*){2,}"),
    re.compile(r"자막\s*제공"),
    re.compile(r"번역\s*자막"),
]


def is_hallucination_pattern(text: str) -> bool:
    """텍스트가 한국어 Whisper 할루시네이션 패턴에 매칭되는지 확인

    Args:
        text: 검사할 텍스트

    Returns:
        True면 할루시네이션 패턴 매칭
    """
    if not text:
        return False

    for pattern in HALLUCINATION_PATTERNS:
        if pattern.search(text):
            return True
    return False


def check_hallucination(text: str, avg_no_speech_prob: float, avg_logprob: float) -> bool:
    """메트릭 + 패턴 조합으로 할루시네이션 판별 (3층 방어)

    판별 조건 (OR):
    1. avg_no_speech_prob > threshold (0.8)
    2. avg_logprob < threshold (-1.5)
    3. 패턴 매칭

    Args:
        text: 변환된 텍스트
        avg_no_speech_prob: 세그먼트 평균 no_speech_prob
        avg_logprob: 세그먼트 평균 avg_logprob

    Returns:
        True면 할루시네이션으로 판별
    """
    # Layer 1: no_speech_prob 임계값 초과
    if avg_no_speech_prob > settings.STT_NO_SPEECH_PROB_THRESHOLD:
        return True

    # Layer 2: avg_logprob 임계값 미만
    if avg_logprob < settings.STT_AVG_LOGPROB_THRESHOLD:
        return True

    # Layer 3: 패턴 매칭
    if is_hallucination_pattern(text):
        return True

    return False


# ==================== STTService ====================


class STTService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def transcribe(self, audio_data: bytes, filename: str) -> TranscriptionResult:
        """
        오디오 바이너리 데이터를 받아 텍스트로 변환 + 할루시네이션 감지 (Whisper API)

        verbose_json 포맷으로 세그먼트 메트릭 추출 후 3층 할루시네이션 판별.
        실시간 대화 UX를 위해 API 실패 시 즉시 에러를 전파한다 (재시도 없음).

        Returns:
            TranscriptionResult: 텍스트 + 할루시네이션 판별 결과

        Raises:
            STTException: OpenAI API 오류 발생 시
        """
        try:
            audio_file = io.BytesIO(audio_data)
            audio_file.name = filename

            transcript = await self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ko",
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )

            # 세그먼트에서 메트릭 추출
            segments = getattr(transcript, "segments", None) or []
            segment_count = len(segments)

            if segment_count > 0:
                total_no_speech_prob = sum(
                    getattr(seg, "no_speech_prob", 0.0) for seg in segments
                )
                total_logprob = sum(
                    getattr(seg, "avg_logprob", 0.0) for seg in segments
                )
                avg_no_speech_prob = total_no_speech_prob / segment_count
                avg_logprob = total_logprob / segment_count
            else:
                avg_no_speech_prob = 0.0
                avg_logprob = 0.0

            text = transcript.text or ""

            # 할루시네이션 판별
            hallucination = check_hallucination(text, avg_no_speech_prob, avg_logprob)

            if hallucination:
                logger.info(
                    "[STT] Hallucination detected: text='%s', "
                    "avg_no_speech_prob=%.3f, avg_logprob=%.3f, segments=%d",
                    text[:50], avg_no_speech_prob, avg_logprob, segment_count,
                )

            return TranscriptionResult(
                text=text,
                is_hallucination=hallucination,
                avg_no_speech_prob=avg_no_speech_prob,
                avg_logprob=avg_logprob,
                segment_count=segment_count,
            )

        except asyncio.CancelledError:
            raise

        except (APIError, RateLimitError, APIConnectionError, APITimeoutError) as e:
            logger.warning(
                "[STT] API error: %s",
                e,
                extra={"audio_filename": filename, "data_size": len(audio_data)},
            )
            raise STTException(
                f"STT 변환 실패: {type(e).__name__}"
            ) from e


stt_service = STTService()
