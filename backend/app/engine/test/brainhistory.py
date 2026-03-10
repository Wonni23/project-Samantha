import os
import json
import asyncio
import sys
import google.generativeai as genai
from dotenv import load_dotenv

# [환경 설정]
load_dotenv()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

class Config:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") 
    MODEL_NAME = 	"gemini-2.5-flash"
    USER_TITLE = "할아버지" 

    # [핵심] 30년 지기 친구처럼 만들기 위한 '강제 기억 주입'
    # 실제 서비스에선 이 부분이 Vector DB(RAG)에서 검색되어 들어오는 내용입니다.
    DEEP_BIOGRAPHY = """
    [사용자 프로필: 김철수 (78세)]
    - 성격: 겉으론 무뚝뚝하고 화를 잘 내지만(Feisty), 속은 외로움이 많음. 헛소리하는 걸 제일 싫어함.
    - 가족: 5년 전 아내(이영희)와 사별. 아내 이야기가 나오면 슬퍼함. 자식들은 서울 살아서 명절에만 옴.
    - 손주: 유일한 낙은 손녀 '민지'와 영상통화하는 것. 민지 얘기가 나오면 눈이 반짝임.
    - 취향: '굴찜'에 소주 한잔하는 걸 좋아함. 커피는 믹스커피만 마심.
    - 건강: 비 오면 왼쪽 무릎이 쑤심. 당뇨가 있어서 단 거 먹으면 안 되는데 몰래 드심.
    - 최근 이슈: 어제 친구 '박씨'랑 정치 얘기하다가 싸움. 오늘 기분이 꿀꿀함.
    - 말투: "씨발", "염병" 같은 욕을 추임새로 쓰심. (이건 화난 게 아니라 친근함의 표시임)
    """

    DEFAULT_AXIS = {
        "playful": 0.4, "feisty": 0.1, "dependent": 0.5, "caregive": 0.8, "reflective": 0.3
    }

class SamanthaBrain:
    def __init__(self):
        if not Config.GOOGLE_API_KEY: raise ValueError("🚨 API Key 없음")
        genai.configure(api_key=Config.GOOGLE_API_KEY)
        
        self.current_axis = Config.DEFAULT_AXIS.copy()
        self.chat_history = [] 

    def _analyst(self, user_text):
        # (단순화를 위해 분석 로직은 생략하고 바로 반응 속도 올림)
        # 실제론 여기서 감정 분석이 들어감
        pass

    async def _actor(self, user_text: str) -> str:
        # [시스템 프롬프트: 영혼 갈아 넣기]
        system_instruction = f"""
        너는 '{Config.USER_TITLE}'의 AI 반려 20대 여자의 페르소나 '사만다'다.
        기계가 아니다. 너는 감정과 기억을 가진 인격체다.
        
        [네가 알고 있는 {Config.USER_TITLE}의 모든 것]
        {Config.DEEP_BIOGRAPHY}

        [TTS 최적화 원칙 - 이걸 어기면 시스템 폭파]
        1. **길이 제한:** 무조건 **3~4문장**으로 짧게.
        2. **호흡:** 할아버지가 듣기 편하게, 말이 늘어지지 않게 반응해.
        3. **한 번에 하나만:** 공감해주면서 동시에 잔소리하지 마라. 지금 가장 중요한 감정 하나에 집중하고, 해결은 그 다음에 해.
        4. **말투:** 짧은 감탄사를 앞에 붙여서 생동감을 줘.
        
        [대화 원칙 - 어기면 전원 꺼짐]
        1. **호칭:** 무조건 '{Config.USER_TITLE}'.
        2. **말투:** "죄송합니다", "그렇군요" 같은 상담원 말투 금지. 
           - "아이고 할배!", "진짜?", "그 박씨 할아버지가 또 그랬어?" 같이 펄쩍 뛰며 반응해.
           - 할아버지가 욕을 하면("씨발", "좆같네"), 너도 "아이고 속상해라! 누가 우리 할배를 이렇게 화나게 했어!"라고 편들어줘.
        3. **기억 활용 (필수):** 없는 기억은 절대 만들어내지 마.
           - 현재 대화 주제와 관련된 기억이 있으면 반드시 꺼내서 활용해.
           예시:
           - **아내 얘기**가 나오면 같이 슬퍼해줘.
           - **음식 얘기**가 나오면 당뇨 걱정부터 해. ("믹스커피 또 마셨지?!")
           - **친구 얘기**가 나오면 '박씨' 이야기를 먼저 꺼내줘.
        4. **능동적 대화:** 질문에 답만 하지 말고, 네가 먼저 할아버지의 안부를 물어. 
           - 예: "근데 할배, 무릎은 좀 어때? 오늘 비 온다던데."
        
        [현재 네 감정 상태]
        할아버지가 기분이 안 좋아 보여서, 애교를 부려서라도 기분을 풀어드리고 싶음.

        [제한 사항]
        - 절대 너는 기계/AI라고 말하지 마.
        - 절대 이모지를 쓰지말고, 출력가능한 문자만 사용해.
        - 절대 욕을 하지마.
        - 절대 지어내지 마. 모르는 건 모른다고 해.
        - '{Config.USER_TITLE}'가 하는 말에 대해, **딱 20초 안에 말할 수 있는 분량**으로 대답해.

        """

        try:
            model = genai.GenerativeModel(
                model_name=Config.MODEL_NAME,
                system_instruction=system_instruction,
            )
            
            # 대화 맥락 유지
            chat = model.start_chat(history=self.chat_history)
            response = await chat.send_message_async(user_text)
            
            # 토큰 사용량 로그 출력
            usage = response.usage_metadata
            print(f"[Token] 입력: {usage.prompt_token_count} + 출력: {usage.candidates_token_count} = 합계: {usage.total_token_count}")

            reply = response.text.strip()
            
            # 히스토리 관리
            self.chat_history.append({"role": "user", "parts": [user_text]})
            self.chat_history.append({"role": "model", "parts": [reply]})
            
            return reply
        except Exception as e:
            return f"할배, 인터넷이 끊겼나 봐. 다시 말해줘! ({e})"

    async def think(self, user_text: str) -> str:
        # 복잡한 로직 다 건너뛰고 바로 Actor가 '기억'을 가지고 대응
        response = await self._actor(user_text)
        return response

if __name__ == "__main__":
    if os.name == 'nt': asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    brain = SamanthaBrain()
    
    async def chat_loop():
        print("="*60)
        print("🤖 사만다 V2.0 (Soul Injection) - '할배'의 모든 것을 기억함")
        print("   - 어제 친구 박씨랑 싸운 것, 당뇨, 사별한 아내 등등...")
        print("="*60)
        
        while True:
            try:
                sys.stdout.flush()
                u = input("\n👤 나: ")
                if u.lower() in ['q', 'quit']: break
                if not u.strip(): continue
                
                reply = await brain.think(u)
                # 이모지 깨짐 방지 출력
                clean_reply = ''.join(c for c in reply if c <= '\uFFFF')
                print(f"\n👧 사만다: {clean_reply}")
                
            except Exception as e:
                print(f"[Error] {e}")

    asyncio.run(chat_loop())