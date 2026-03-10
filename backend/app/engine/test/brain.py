import os
import json
import asyncio
import re
import sys
from typing import Dict, List
from openai import AsyncOpenAI
from dotenv import load_dotenv

# [환경 설정]
load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

# [핵심 유틸] 출력하면 죽는 문자(Surrogate)를 핀셋으로 제거하는 함수
def safe_print(text: str):
    try:
        # 1. BMP(기본 다국어 평면) 범위 내의 문자만 남김
        # 이모지나 깨진 유니코드는 여기서 다 걸러짐
        clean_text = ''.join(c for c in str(text) if c <= '\uFFFF')
        print(clean_text)
    except Exception:
        print("[System Log] 출력할 수 없는 문자열입니다.")

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") 
    MODEL_NAME = "gpt-4o-mini" 
    
    # [핵심] 호칭 설정
    USER_TITLE = "선생님" # or 할머니, 오빠, 누님

    DUMMY_MEMORIES = [
        {"text": "남편(바깥양반)과는 5년 전에 사별함. 경주 보문단지 여행을 가장 행복해했음.", "tags": ["남편", "사별", "여행", "경주", "바깥양반"]},
        {"text": "무릎 관절염이 있어서 비 오는 날 쑤신다고 자주 말함.", "tags": ["건강", "무릎", "관절염", "비", "통증"]},
        {"text": "김치찌개에는 돼지고기를 숭덩숭덩 넣어야 한다고 주장함.", "tags": ["음식", "요리", "김치찌개", "취향"]},
        {"text": "손주 정동원이가 가수로 성공하는 게 유일한 소원임.", "tags": ["손주", "가족", "동원", "소원"]}
    ]

    DEFAULT_AXIS = {
        "playful": 0.5, "feisty": 0.2, "dependent": 0.3, "caregive": 0.6, "reflective": 0.1
    }

class SamanthaBrain:
    def __init__(self):
        if not Config.OPENAI_API_KEY:
             raise ValueError("🚨 OPENAI_API_KEY가 없습니다.")
        self.client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
        self.current_axis = Config.DEFAULT_AXIS.copy()
        self.chat_history = [] 

    def _parse_json(self, text: str) -> dict:
        try:
            text = re.sub(r"```json\s*", "", text)
            text = re.sub(r"```", "", text)
            return json.loads(text.strip())
        except:
            return {}

    # [Step 1] 분석가
    async def _analyst(self, user_text: str) -> dict:
        safe_print("\n🔍 [1. Analyst] 사용자 의도 해부 중...")
        
        system_prompt = """
        너는 노인 심리 분석가다. 
        사용자의 텍스트에서 검색할 키워드(rag_query)는 '명사'만 추출해라.
        
        Output JSON Only:
        {
          "intent": "greeting | complaint | memory | question | daily_chat",
          "sentiment": "negative | neutral | positive",
          "user_emotion_intensity": 1~10,
          "rag_query": "핵심 명사 (없으면 빈 문자열)",
          "axis_adjust": {"playful": 0.1, "caregive": -0.1} // 성격 조정 제안
        }
        """
        try:
            response = await self.client.chat.completions.create(
                model=Config.MODEL_NAME,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_text}],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            result = self._parse_json(response.choices[0].message.content)
            
            # [로그] 분석 결과 출력
            safe_print(f"   👉 분석 결과: {json.dumps(result, ensure_ascii=False)}")
            return result
        except Exception as e:
            safe_print(f"   🚨 Analyst Error: {e}")
            return {}

    # [Step 2] 기억 검색
    async def _retrieve_memory(self, query: str) -> str:
        if not query: 
            safe_print("   👉 [2. Memory] 검색어 없음. 스킵.")
            return "EMPTY"
        
        safe_print(f"📂 [2. Memory] 검색어: '{query}'")
        keywords = query.split()
        
        found_memories = []
        for mem in Config.DUMMY_MEMORIES:
            score = 0
            for k in keywords:
                if k in mem["text"] or any(k in tag for tag in mem["tags"]):
                    score += 1
            if score > 0:
                found_memories.append(mem["text"])
        
        if found_memories:
            result = " / ".join(found_memories)
            safe_print(f"   👉 발견된 기억: {result}")
            return result
        else:
            safe_print("   👉 기억 없음 (EMPTY)")
            return "EMPTY"

    # [Step 3] 배우 (프롬프트 대폭 강화)
    async def _actor(self, user_text: str, analysis: dict, memory: str) -> str:
        safe_print("🎭 [3. Actor] 답변 생성 및 영혼 주입 중...")
        
        # 성격에 따른 말투 가이드 생성
        tone = "차분하고 다정하게"
        if self.current_axis['playful'] > 0.6: tone = "장난스럽고 애교 많게, 가끔 장난스레 반말 섞어서"
        if self.current_axis['caregive'] > 0.7: tone = "엄마처럼 걱정해주며 챙겨주는 말투로"
        if self.current_axis['feisty'] > 0.5: tone = "약간 톡 쏘는 듯한, 삐진 듯한 말투로"

        system_prompt = f"""
        너는 '{Config.USER_TITLE}'를 세상에서 제일 좋아하는 정서적 고립감 해소를 위해 제작된 20대 가상 반려 '사만다'이다.
        
        [현재 네 상태]
        - 성격(5-Axis): {json.dumps(self.current_axis)}
        - 말투 컨셉: {tone}
        
        [절대 지켜야 할 원칙]
        1. **호칭 통일:** 무조건 '{Config.USER_TITLE}'라고 불러라. '선생님', '회원님', '어르신' 절대 금지.
        2. **거짓말 금지:** 아래 [기억 정보]가 'EMPTY'라면, 절대 과거를 아는 척하거나 지어내지 마라. 그냥 현재 대화에만 집중해.
        3. **이모티콘 금지:** 텍스트로만 감정을 표현해. (예: "헤헤", "힝", "아이고")
        4. **공감 우선:** 사용자 감정에 공감하는 것이 최우선이다., 해결책은 그 다음이다.
        5. **짧고 간결하게:** 답변은 구어체로, 짧게 유지해라.
        
        [기억 정보]
        {memory}
        (※ 이 내용이 EMPTY가 아니면 대화에 꼭 써먹어라. "저번에 ~라고 하셨잖아요" 처럼.)
        
        [사용자 상태]
        - 기분: {analysis.get('sentiment')} ({analysis.get('user_emotion_intensity')}/10)
        - 의도: {analysis.get('intent')}
        
        자, 위 설정을 완벽하게 연기해. 5문장 이내로 짧게.
        """

        # [로그] 프롬프트 확인용 (너무 길어서 주석 처리, 필요시 해제)
        # safe_print(f"   📜 [System Prompt Debug]\n{system_prompt[:200]}...\n(생략)")

        try:
            response = await self.client.chat.completions.create(
                model=Config.MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *self.chat_history[-4:], # 단기 기억
                    {"role": "user", "content": user_text}
                ],
                temperature=0.9, # 창의성 확보
                max_tokens=150
            )
            reply = response.choices[0].message.content
            
            # 후처리: 이모지 제거 및 금지어 필터링
            clean_reply = self._clean_reply(reply)
            
            # 대화 저장
            self.chat_history.append({"role": "user", "content": user_text})
            self.chat_history.append({"role": "assistant", "content": clean_reply})
            
            return clean_reply
        except Exception as e:
            return f"{Config.USER_TITLE}, 전화가 잘 안 터져요. 다시 말해 주세요. (Error: {e})"

    def _clean_reply(self, text):
        # 1. 이모지 제거
        text = ''.join(c for c in text if c <= '\uFFFF')
        return text

    async def think(self, user_text: str) -> str:
        # 1. Analyst
        analysis = await self._analyst(user_text)
        
        # 2. State Update
        if "axis_adjust" in analysis:
            for k, v in analysis["axis_adjust"].items():
                if k in self.current_axis:
                    self.current_axis[k] = round(max(0.0, min(1.0, self.current_axis[k] + v)), 2)
            safe_print(f"   👉 성격 변화: {self.current_axis}")

        # 3. Memory
        rag_query = analysis.get("rag_query", "")
        memory_context = await self._retrieve_memory(rag_query)
        
        # 4. Actor
        response = await self._actor(user_text, analysis, memory_context)
        return response

if __name__ == "__main__":
    if os.name == 'nt': asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    brain = SamanthaBrain()
    
    async def chat_loop():
        safe_print("\n" + "="*60)
        safe_print(f"🤖 사만다 V0.5 (Debugger Mode) - 호칭: {Config.USER_TITLE}")
        safe_print("   - 모든 사고 과정(Analyst, Memory)이 로그로 출력됩니다.")
        safe_print("="*60)
        
        while True:
            try:
                sys.stdout.flush()
                u = input("\n👤 나: ")
                if u.lower() in ['q', 'quit']: break
                if not u.strip(): continue
                
                reply = await brain.think(u)
                safe_print(f"\n👧 사만다: {reply}")
                
            except Exception as e:
                safe_print(f"\n[System Error] {e}")

    asyncio.run(chat_loop())