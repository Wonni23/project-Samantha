# app/models/enums.py
from enum import Enum

class PersonaType(str, Enum):
    SIA_MALE = "sia_male"
    SIA_FEMALE = "sia_female"

class PlatformType(str, Enum):
    ANDROID = "android"
    IOS = "ios"
    WEB = "web"

class GenderType(str, Enum):
    MALE = "male"
    FEMALE = "female"

class UserTier(str, Enum):
    FREE = "free"                # 찍먹
    B2C_BASIC = "b2c_basic"      # 월 9,900원 (제한 있음)
    B2C_PREMIUM = "b2c_premium"  # 월 19,900원 (무제한)
    B2G_WELFARE = "b2g_welfare"  # 지자체 보급형

class UserRole(str, Enum):
    USER = "user"             # 일반 사용자 (노인)
    GUARDIAN = "guardian"     # 보호자 (결제셔틀 & 모니터링)
    B2G_ADMIN = "b2g_admin"   # 지자체 담당자 (관제용)
    SUPER_ADMIN = "admin"     # 개발팀/운영팀 (God Mode)

class RiskType(str, Enum):
    DEPRESSION = "depression"
    DEMENTIA = "dementia"
    SUICIDE = "suicide_risk"     # RedLine
    SCAM = "scam"
    EMERGENCY = "emergency"

class PaymentMethod(str, Enum):
    WEB_PG = "web_pg"            # 토스/나이스 (효도결제)
    ONE_STORE = "one_store"      # 휴대폰 소액결제 (자립형 노인)
    GALAXY_STORE = "galaxy_store" # 삼성페이 (인텔리 노인)

class LegacyCategory(str, Enum):
    """레거시 저장 카테고리 (DB 저장용, lowercase)"""
    EPISODE = "episode"    # 과거 에피소드 (건강/관계/경력 등 사건)
    VALUE = "value"        # 가치관/선호/취향


class SpeakerType(str, Enum):
    USER = "user"
    AI = "ai"

class ProcessingStatus(str, Enum):
    PENDING = "pending"       # 대기 중 (아직 처리 안 됨)
    COMPLETED = "completed"   # 처리 성공 (VectorDB 적재 완료)
    FAILED = "failed"         # 에러 발생 (재시도 필요)
    IGNORED = "ignored"       # 처리 하려 했으나 가치가 없어서 버림 (ex: "ㅋㅋ" 같은 단답)

class RoutineType(str, Enum):
    # [Care & Health] - 기존 돌봄 영역
    MEDICATION = "medication" # 투약
    MEAL = "meal"             # 식사
    SLEEP = "sleep"           # 기상/취침
    HOSPITAL = "hospital"     # 병원 방문
    EXERCISE = "exercise"     # 산책/운동 (요가, 스트레칭 포함)

    # [Active & Social] - 액티브 시니어 영역
    SOCIAL = "social"         # 사교 모임 (가족, 골프, 동창회, 점심 약속)
    HOBBY = "hobby"           # 취미 및 자기계발 (바둑, 서예, 스마트폰 강좌)
    RELIGION = "religion"     # 종교 활동 (예배, 법회, 기도 시간)

# [2. Quest System Enums] - 퀘스트/미션 관련
class QuestType(str, Enum):
    PEDOMETER = "pedometer"       # 만보기 (500보 걷기)
    PHOTO = "photo"               # 비전 인식 (꽃, 음식 찍기)
    LOCATION = "location"         # GPS 인증 (경로당, 복지관 방문)
    INTERACTION = "interaction"   # 대화 미션 (특정 주제로 대화하기)
    COGNITIVE = "cognitive"       # 치매 예방 퀴즈 (B2G KPI용)

class QuestStatus(str, Enum):
    IN_PROGRESS = "in_progress"   # 진행 중
    COMPLETED = "completed"       # 성공 (보상 지급 대기)
    REWARDED = "rewarded"         # 보상 수령 완료
    FAILED = "failed"             # 실패 (조건 불충족)
    EXPIRED = "expired"           # 기간 만료 (시간 제한 퀘스트)

# [3. Store & Item Enums] - B2C 상점/스킨 관련
class ItemCategory(str, Enum):
    OUTFIT = "outfit"       # 옷 (한복, 정장) - Body Layer
    HEAD = "head"           # 머리 장식 (모자, 삔) - Head Layer
    HAND = "hand"           # 손에 드는 것 (꽃, 우산, 숟가락) - Hand Layer
    BACKGROUND = "background" # 배경 화면 (기와집, 아파트, 공원)
    CONSUMABLE = "consumable" # 소모품 (영양제, 커피 - 먹으면 사라짐/모션발동)

class ItemRarity(str, Enum):
    COMMON = "common"       # 일반 (상점 상시 판매)
    RARE = "rare"           # 희귀 (특정 시즌/퀘스트 보상)
    EPIC = "epic"           # 영웅 (유료 결제 전용)
    LEGENDARY = "legendary" # 전설 (B2G 표창, 장기 근속 보상)