# app/integrations/llm/openai.py
"""
OpenAI 인터페이스 구현
"""

import asyncio
import logging
from typing import List
from openai import (
    AsyncOpenAI,
    APIError,
    RateLimitError,
    APIConnectionError,
    APITimeoutError,
)

from app.integrations.llm.base import BaseEmbeddingProvider
from app.core.config import settings
from app.core.exceptions import EmbeddingException

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_BACKOFF_BASE = 1.0  # 1s, 2s, 4s


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI 임베딩"""

    def __init__(self):
        """OpenAI 클라이언트 초기화"""
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.EMBEDDING_MODEL

    async def get_embedding(self, text: str) -> List[float]:
        """
        OpenAI를 사용하여 텍스트의 임베딩 벡터 생성

        Args:
            text: 입력 텍스트

        Returns:
            1536차원 임베딩 벡터 (text-embedding-3-small)

        Raises:
            EmbeddingException: 모든 재시도 실패 시
            ValueError: 빈 텍스트 등 입력 오류
        """
        text = text.replace("\n", " ").strip()

        if not text:
            raise ValueError("빈 텍스트에 대한 임베딩을 생성할 수 없습니다")

        for attempt in range(_MAX_RETRIES):
            try:
                response = await self.client.embeddings.create(
                    input=text,
                    model=self.model,
                )

                if not response or not hasattr(response, 'data'):
                    raise ValueError("OpenAI 응답에 data 필드가 없습니다")

                if not response.data or len(response.data) == 0:
                    raise ValueError("OpenAI 응답의 data가 비어있습니다")

                if not hasattr(response.data[0], 'embedding'):
                    raise ValueError("OpenAI 응답에 embedding 필드가 없습니다")

                embedding = response.data[0].embedding
                if not embedding or len(embedding) == 0:
                    raise ValueError("OpenAI 임베딩 벡터가 비어있습니다")

                return embedding

            except ValueError:
                raise

            except (RateLimitError, APIConnectionError, APITimeoutError, APIError) as e:
                logger.warning(
                    "OpenAI 임베딩 일시 오류 attempt %d/%d: %s",
                    attempt + 1, _MAX_RETRIES, e,
                )
                if attempt == _MAX_RETRIES - 1:
                    raise EmbeddingException(
                        f"임베딩 생성 실패 ({_MAX_RETRIES}회 재시도 후): {type(e).__name__}"
                    ) from e
                await asyncio.sleep(_BACKOFF_BASE * (2 ** attempt))

            except Exception as e:
                logger.error(f"OpenAI 임베딩 예기치 않은 오류: {e}", exc_info=True)
                raise

        raise EmbeddingException("임베딩 생성 실패: 예기치 않은 상태")
