FROM python:3.12-slim

WORKDIR /app

# 시스템 의존성 설치 (필요시 gcc 등 추가)
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# 패키지 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스코드 복사
COPY . .

COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# 실행 명령어 (자동 마이그레이션 포함)
CMD ["sh", "entrypoint.sh"]