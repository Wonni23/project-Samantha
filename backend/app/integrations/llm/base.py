# app/integrations/llm/base.py
"""
LLM의 공통 인터페이스 정의
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class GenerationConfig:
    """LLM 생성 설정"""
    temperature: float = 0.7
    max_output_tokens: int = 1000
    top_p: float = 0.9
    top_k: int = 40

    def __post_init__(self) -> None:
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError(f"temperature must be 0.0~2.0, got {self.temperature}")
        if not 0.0 <= self.top_p <= 1.0:
            raise ValueError(f"top_p must be 0.0~1.0, got {self.top_p}")
        if self.top_k < 1:
            raise ValueError(f"top_k must be >= 1, got {self.top_k}")
        if self.max_output_tokens < 1:
            raise ValueError(f"max_output_tokens must be >= 1, got {self.max_output_tokens}")


class BaseLLMProvider(ABC):
    """LLM의 기본 인터페이스"""
    
    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None
    ) -> str:
        """
        프롬프트로부터 텍스트 생성

        Args:
            prompt: 입력 프롬프트
            config: 생성 설정

        Returns:
            생성된 텍스트
        """
        pass
    
    @abstractmethod
    async def generate_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        config: Optional[GenerationConfig] = None
    ) -> str:
        """
        히스토리와 함께 채팅 응답 생성

        Args:
            messages: 'role'과 'content'를 포함한 메시지 딕셔너리 리스트
            system_prompt: 선택적 시스템 프롬프트
            config: 생성 설정

        Returns:
            생성된 응답
        """
        pass
    
    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        config: Optional[GenerationConfig] = None
    ) -> Dict[str, Any]:
        """
        구조화된 JSON 출력 생성

        Args:
            prompt: 입력 프롬프트
            config: 생성 설정

        Returns:
            파싱된 JSON 딕셔너리
        """
        pass


class BaseEmbeddingProvider(ABC):
    """임베딩 기본 인터페이스"""

    @abstractmethod
    async def get_embedding(self, text: str) -> List[float]:
        """
        텍스트의 임베딩 벡터 생성

        Args:
            text: 입력 텍스트

        Returns:
            임베딩 벡터
        """
        pass
