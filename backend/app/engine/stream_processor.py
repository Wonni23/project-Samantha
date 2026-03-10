# backend/app/engine/stream_processor.py
"""
파이프라인 스트림 처리기

SentenceSegmenter: LLM 스트리밍 chunk → TTS용 문장 단위 분리
StreamingJsonParser: Actor JSON 스트림 → response_text 실시간 추출 + control signals 파싱
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from app.schemas.session_schema import AxisUpdates
from app.schemas.conversation_schema import ConversationTracker

logger = logging.getLogger(__name__)

# 강한 경계: 문장 종결 부호
_STRONG_BOUNDARY_RE = re.compile(r"[.!?。\n]|[！？]")

# 약한 경계: 쉼표, 콜론 등
_WEAK_BOUNDARY_RE = re.compile(r"[,，:;…]|[、]")


@dataclass
class Segment:
    """TTS로 전송할 문장 세그먼트"""
    text: str
    is_final: bool = False


class SentenceSegmenter:
    """
    LLM chunk 스트림을 받아서 TTS용 문장/구절 단위로 분리하는 버퍼.

    [사용법]
    segmenter = SentenceSegmenter()

    async for chunk in llm.generate_stream(...):
        # UI에는 즉시 전송
        yield {"type": "text", "data": chunk}

        # TTS에는 문장 단위로
        for seg in segmenter.feed(chunk):
            yield {"type": "tts", "data": seg.text}

    # 스트림 종료 시 남은 버퍼 처리
    for seg in segmenter.flush():
        yield {"type": "tts", "data": seg.text}

    [튜닝 포인트 - 한국어 기준]
    - min_chars: 30~50 (너무 낮으면 끊김)
    - max_chars: 140~220 (한 번에 숨 쉬는 길이)
    - soft_timeout_ms: 600~1000 (구두점 없는 말버릇 대응)
    """

    def __init__(
        self,
        *,
        min_chars: int = 35,
        max_chars: int = 180,
        soft_timeout_ms: int = 800,
    ):
        """
        Args:
            min_chars: 최소 문장 길이 (이보다 짧으면 버퍼링)
            max_chars: 최대 문장 길이 (이보다 길면 강제 분리)
            soft_timeout_ms: 구두점 없어도 일정 시간 지나면 분리
        """
        self.min_chars = min_chars
        self.max_chars = max_chars
        self.soft_timeout_ms = soft_timeout_ms

        self._buf: str = ""
        self._last_emit_ts = time.monotonic()

    def feed(self, chunk: str) -> list[Segment]:
        """
        chunk를 버퍼에 추가하고, 방출 가능한 문장 세그먼트들을 반환.

        Args:
            chunk: LLM에서 받은 텍스트 청크

        Returns:
            방출 가능한 Segment 리스트 (비어있을 수 있음)
        """
        if not chunk:
            return []

        self._buf += chunk
        out: list[Segment] = []

        while True:
            seg = self._try_cut_segment()
            if seg is None:
                break
            out.append(Segment(seg))

        return out

    def flush(self) -> list[Segment]:
        """
        스트림 종료 시 남은 버퍼를 모두 방출.

        Returns:
            남은 텍스트의 Segment 리스트
        """
        text = self._buf.strip()
        self._buf = ""
        if not text:
            return []
        return [Segment(text, is_final=True)]

    def _try_cut_segment(self) -> str | None:
        """버퍼에서 세그먼트를 잘라낼 수 있는지 시도"""
        buf = self._buf

        # 1) 강한 경계(종결/개행)가 있으면 거기까지 자르기
        m = _STRONG_BOUNDARY_RE.search(buf)
        if m:
            cut_idx = m.end()
            candidate = buf[:cut_idx].strip()
            rest = buf[cut_idx:]
            if candidate:
                self._buf = rest
                self._last_emit_ts = time.monotonic()
                return candidate

        # 2) 최대 길이를 넘으면, 가장 가까운 약한 경계/공백에서 자르기
        if len(buf) >= self.max_chars:
            cut_idx = self._best_cut_index(buf, prefer_weak=True)
            candidate = buf[:cut_idx].strip()
            self._buf = buf[cut_idx:]
            self._last_emit_ts = time.monotonic()
            return candidate if candidate else None

        # 3) 최소 길이를 넘었고, 약한 경계가 있으면 자르기
        if len(buf) >= self.min_chars:
            weak = list(_WEAK_BOUNDARY_RE.finditer(buf))
            if weak:
                cut_idx = weak[-1].end()
                candidate = buf[:cut_idx].strip()
                self._buf = buf[cut_idx:]
                self._last_emit_ts = time.monotonic()
                return candidate if candidate else None

        # 4) 타임아웃: 구두점이 안 와도 일정 시간 지나면 공백 기준으로 자르기
        elapsed_ms = (time.monotonic() - self._last_emit_ts) * 1000
        if len(buf) >= self.min_chars and elapsed_ms >= self.soft_timeout_ms:
            cut_idx = self._best_cut_index(buf, prefer_weak=False)
            candidate = buf[:cut_idx].strip()
            self._buf = buf[cut_idx:]
            self._last_emit_ts = time.monotonic()
            return candidate if candidate else None

        return None

    def _best_cut_index(self, buf: str, *, prefer_weak: bool) -> int:
        """
        자를 위치를 찾는다.

        Args:
            buf: 버퍼 문자열
            prefer_weak: True면 약한 경계를 우선 고려

        Returns:
            자를 위치 인덱스
        """
        upper = min(len(buf), self.max_chars)

        if prefer_weak:
            weak = list(_WEAK_BOUNDARY_RE.finditer(buf[:upper]))
            if weak:
                return weak[-1].end()

        # 공백 기준
        space_idx = buf.rfind(" ", 0, upper)
        if space_idx != -1 and space_idx >= 10:
            return space_idx + 1  # 공백 포함해서 끊기

        # 공백도 없으면 그냥 upper
        return upper


# ============ Streaming JSON Parser ============


class _ParserState(Enum):
    """StreamingJsonParser 내부 상태"""
    ACCUMULATING_PREFIX = "accumulating_prefix"
    STREAMING_TEXT = "streaming_text"
    ACCUMULATING_SUFFIX = "accumulating_suffix"
    DONE = "done"
    PLAIN_TEXT = "plain_text"


# response_text 마커: JSON에서 이 패턴 이후가 실제 응답 텍스트
_RESPONSE_TEXT_MARKER = '"response_text"'

# control 필드 키 탐색용 (값 추출은 _extract_json_object로 수행)
_CONTROL_FIELD_RE = re.compile(
    r'"(conversation_tracker|axis_updates)"\s*:\s*'
)


def _extract_json_object(text: str, start: int) -> Optional[str]:
    """text[start]의 '{'부터 매칭되는 '}'까지 JSON 객체를 추출.

    JSON 문자열 내부의 {, }는 무시하고 이스케이프를 인식하므로,
    정규식 [^}]* 방식의 조기 절단 문제가 없다.

    Returns:
        추출된 JSON 문자열, 또는 불완전하면 None.
    """
    if start >= len(text) or text[start] != '{':
        return None

    depth = 0
    in_string = False
    escape_next = False

    for i in range(start, len(text)):
        ch = text[i]

        if escape_next:
            escape_next = False
            continue

        if ch == '\\' and in_string:
            escape_next = True
            continue

        if ch == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]

    return None


@dataclass
class StreamParserResult:
    """StreamingJsonParser.feed()의 반환값"""
    text_chunks: List[str] = field(default_factory=list)
    axis_updates: Optional[AxisUpdates] = None
    conversation_tracker: Optional[ConversationTracker] = None
    is_done: bool = False


class StreamingJsonParser:
    """
    Actor의 JSON 스트림을 점진적으로 파싱하는 상태 머신.

    Actor 출력 JSON 구조 (두 가지 순서 모두 지원):
    순서 A (text-first, 기본):
    {
        "response_text": "..."     ← 즉시 스트리밍 시작
        "live2d_control": {...},   ← suffix에서 추출
        "tts_config": {...},       ← suffix에서 추출
    }
    순서 B (control-first, 하위 호환):
    {
        "live2d_control": {...},   ← prefix에서 추출
        "tts_config": {...},       ← prefix에서 추출
        "response_text": "..."     ← 스트리밍 대상
    }

    [상태 전이]
    ACCUMULATING_PREFIX → STREAMING_TEXT → ACCUMULATING_SUFFIX → DONE
          ↓ (JSON 아닌 경우)
      PLAIN_TEXT (fallback)

    [사용법]
    parser = StreamingJsonParser()
    async for chunk in actor.generate_stream(context):
        result = parser.feed(chunk)
        if result.tts_config:
            yield {"type": "tts_config", "data": result.tts_config}
        for text in result.text_chunks:
            yield {"type": "text", "data": text}
    final = parser.finish()
    """

    def __init__(self) -> None:
        self._state = _ParserState.ACCUMULATING_PREFIX
        self._prefix_buf: str = ""
        self._text_buf: str = ""  # STREAMING_TEXT 상태에서 이스케이프 처리용
        self._full_text: str = ""  # 누적된 전체 response_text (DB 저장용)
        self._axis_updates: Optional[AxisUpdates] = None
        self._conversation_tracker: Optional[ConversationTracker] = None
        self._suffix_buf: str = ""  # ACCUMULATING_SUFFIX 상태에서 suffix 수집용
        self._escape_pending: bool = False  # 이전 chunk가 \로 끝났는지

    @property
    def full_response_text(self) -> str:
        """누적된 전체 response_text (DB 저장/CancelledError 복구용)"""
        return self._full_text

    def feed(self, chunk: str) -> StreamParserResult:
        """
        새 chunk를 처리하고 결과 반환.

        Args:
            chunk: LLM에서 받은 텍스트 청크 (토큰 단위)

        Returns:
            StreamParserResult: 추출된 텍스트 청크, 설정값 등
        """
        if not chunk:
            return StreamParserResult()

        if self._state == _ParserState.DONE:
            return StreamParserResult(is_done=True)

        if self._state == _ParserState.PLAIN_TEXT:
            return self._handle_plain_text(chunk)

        if self._state == _ParserState.ACCUMULATING_SUFFIX:
            return self._handle_suffix(chunk)

        if self._state == _ParserState.ACCUMULATING_PREFIX:
            return self._handle_prefix(chunk)

        if self._state == _ParserState.STREAMING_TEXT:
            return self._handle_streaming_text(chunk)

        return StreamParserResult()

    def finish(self) -> StreamParserResult:
        """
        스트림 종료 시 호출. 남은 버퍼를 처리.

        Returns:
            StreamParserResult: 남은 텍스트 등
        """
        result = StreamParserResult(is_done=True)

        if self._state == _ParserState.ACCUMULATING_PREFIX:
            # prefix만 쌓이고 response_text 마커를 못 찾은 경우 → fallback
            text = self._prefix_buf.strip()
            if text:
                # JSON에서 response_text를 추출 시도
                extracted = self._try_extract_response_text_from_complete_json(text)
                if extracted:
                    result.text_chunks = [extracted]
                    self._full_text += extracted
                else:
                    result.text_chunks = [text]
                    self._full_text += text

        elif self._state == _ParserState.STREAMING_TEXT:
            # 스트리밍 중 종료 — 남은 이스케이프 처리 텍스트 방출
            if self._text_buf:
                result.text_chunks = [self._text_buf]
                self._full_text += self._text_buf
                self._text_buf = ""

        elif self._state == _ParserState.ACCUMULATING_SUFFIX:
            # suffix에서 control signals 추출
            self._parse_control_objects(self._suffix_buf)

        elif self._state == _ParserState.PLAIN_TEXT:
            pass  # 이미 즉시 전달됨

        self._state = _ParserState.DONE
        result.axis_updates = self._axis_updates
        result.conversation_tracker = self._conversation_tracker
        return result

    def _handle_prefix(self, chunk: str) -> StreamParserResult:
        """ACCUMULATING_PREFIX 상태: response_text 마커 탐색"""
        result = StreamParserResult()

        # 첫 의미 있는 문자로 JSON 여부 판단 ({ 또는 [ 로 시작)
        if not self._prefix_buf and not chunk.lstrip().startswith(("{", "[")):
            self._state = _ParserState.PLAIN_TEXT
            self._full_text += chunk
            result.text_chunks = [chunk]
            return result

        self._prefix_buf += chunk

        # response_text 마커 탐색
        marker_idx = self._prefix_buf.find(_RESPONSE_TEXT_MARKER)
        if marker_idx == -1:
            return result

        # 마커 발견: prefix에서 axis_updates, conversation_tracker 파싱
        prefix_section = self._prefix_buf[:marker_idx]
        self._parse_control_objects(prefix_section)
        result.axis_updates = self._axis_updates
        result.conversation_tracker = self._conversation_tracker

        # 마커 이후에서 여는 따옴표 찾기: "response_text" : "
        after_marker = self._prefix_buf[marker_idx + len(_RESPONSE_TEXT_MARKER):]
        quote_idx = after_marker.find('"')
        if quote_idx == -1:
            # 아직 여는 따옴표가 안 왔음 — 계속 대기
            return result

        # 여는 따옴표 이후가 실제 텍스트 시작
        text_start = after_marker[quote_idx + 1:]
        self._state = _ParserState.STREAMING_TEXT

        # 텍스트 시작 부분이 있으면 처리
        if text_start:
            inner_result = self._handle_streaming_text(text_start)
            result.text_chunks = inner_result.text_chunks
            result.is_done = inner_result.is_done

        return result

    def _handle_streaming_text(self, chunk: str) -> StreamParserResult:
        """STREAMING_TEXT 상태: response_text 내용 실시간 추출"""
        result = StreamParserResult()
        text_chunks: List[str] = []
        i = 0

        while i < len(chunk):
            char = chunk[i]

            if self._escape_pending:
                # 이전 chunk에서 \로 끝난 경우
                self._escape_pending = False
                escaped = self._resolve_escape(char)
                self._text_buf += escaped
                i += 1
                continue

            if char == '\\':
                # 다음 문자 확인
                if i + 1 < len(chunk):
                    next_char = chunk[i + 1]
                    escaped = self._resolve_escape(next_char)
                    self._text_buf += escaped
                    i += 2
                    continue
                else:
                    # chunk 끝에서 \ — 다음 chunk에서 이어서 처리
                    self._escape_pending = True
                    i += 1
                    continue

            if char == '"':
                # response_text 닫는 따옴표 → suffix 수집으로 전이
                if self._text_buf:
                    text_chunks.append(self._text_buf)
                    self._full_text += self._text_buf
                    self._text_buf = ""
                # 남은 chunk → suffix 버퍼
                remainder = chunk[i + 1:]
                if remainder:
                    self._suffix_buf += remainder
                self._state = _ParserState.ACCUMULATING_SUFFIX
                result.text_chunks = text_chunks
                return result

            self._text_buf += char
            i += 1

        # chunk 끝까지 처리 — 버퍼에 쌓인 텍스트 방출
        if self._text_buf:
            text_chunks.append(self._text_buf)
            self._full_text += self._text_buf
            self._text_buf = ""

        result.text_chunks = text_chunks
        return result

    def _handle_suffix(self, chunk: str) -> StreamParserResult:
        """ACCUMULATING_SUFFIX 상태: response_text 이후 JSON 수집"""
        self._suffix_buf += chunk
        return StreamParserResult()

    def _handle_plain_text(self, chunk: str) -> StreamParserResult:
        """PLAIN_TEXT 상태: JSON이 아닌 응답을 그대로 전달"""
        self._full_text += chunk
        return StreamParserResult(text_chunks=[chunk])

    def _parse_control_objects(self, text: str) -> None:
        """prefix 또는 suffix에서 control 필드를 JSON-aware brace matching으로 추출"""
        for match in _CONTROL_FIELD_RE.finditer(text):
            field_name = match.group(1)
            obj_start = match.end()

            json_str = _extract_json_object(text, obj_start)
            if not json_str:
                continue

            try:
                obj = json.loads(json_str)
                if field_name == "conversation_tracker" and self._conversation_tracker is None:
                    self._conversation_tracker = ConversationTracker(**obj)
                elif field_name == "axis_updates" and self._axis_updates is None:
                    self._axis_updates = AxisUpdates(**obj)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse {field_name} JSON: {json_str[:100]}")
            except (TypeError, ValueError) as e:
                logger.warning(f"Failed to validate {field_name}: {e}")

    def _try_extract_response_text_from_complete_json(self, text: str) -> Optional[str]:
        """완전한 JSON에서 response_text 추출 시도 (finish fallback용)"""
        try:
            data = json.loads(text)
            # 배열 래핑 언래핑: [{...}] → {...}
            if isinstance(data, list):
                if len(data) > 0 and isinstance(data[0], dict):
                    data = data[0]
                else:
                    return None
            if isinstance(data, dict):
                # analysis 블록에서 control 필드 추출
                analysis = data.get("analysis", {}) or {}
                if "axis_updates" in analysis and self._axis_updates is None:
                    try:
                        self._axis_updates = AxisUpdates(**analysis["axis_updates"])
                    except (TypeError, ValueError):
                        pass
                if "conversation_tracker" in analysis and self._conversation_tracker is None:
                    try:
                        self._conversation_tracker = ConversationTracker(**analysis["conversation_tracker"])
                    except (TypeError, ValueError):
                        pass
                return data.get("response_text", "")
        except json.JSONDecodeError:
            pass
        return None

    @staticmethod
    def _resolve_escape(char: str) -> str:
        """JSON 이스케이프 시퀀스를 실제 문자로 변환"""
        escape_map = {
            '"': '"',
            '\\': '\\',
            'n': '\n',
            'r': '\r',
            't': '\t',
            '/': '/',
            'b': '\b',
            'f': '\f',
        }
        return escape_map.get(char, '\\' + char)
