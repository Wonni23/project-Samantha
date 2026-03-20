#!/bin/bash

# Samantha 개발 환경 관리 스크립트
# 사용법: ./dev.sh [start|stop|backend|frontend|infra|migrate|status|logs]

set -e

# 색상 정의
GREEN=$'\033[0;32m'
RED=$'\033[0;31m'
YELLOW=$'\033[1;33m'
BLUE=$'\033[0;34m'
NC=$'\033[0m' # No Color

# PID 파일 경로
BACKEND_PID_FILE=".backend.pid"
FRONTEND_PID_FILE=".frontend.pid"

# OS 감지: venv activate 경로 결정
detect_venv_activate() {
    local venv_dir="$1"
    if [[ "$(uname -s)" =~ MINGW|MSYS|CYGWIN ]] || [ -n "$WINDIR" ]; then
        echo "${venv_dir}/Scripts/activate"
    else
        echo "${venv_dir}/bin/activate"
    fi
}

VENV_ACTIVATE=$(detect_venv_activate ".venv")

# 로그 함수
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# 사용법 출력
usage() {
    cat << EOF
${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}
${GREEN}🚀 Samantha 개발 환경 관리 스크립트${NC}
${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}

사용법: ./dev.sh [명령어]

${YELLOW}명령어:${NC}
  ${GREEN}start${NC}      전체 시작 (인프라 + 마이그레이션 + 백엔드 + 프론트엔드)
  ${GREEN}stop${NC}       전체 중지 (볼륨 유지)
  ${GREEN}clean${NC}      전체 중지 및 볼륨(DB, 스토리지) 삭제
  ${GREEN}backend${NC}    백엔드만 시작 (인프라 자동 시작)
  ${GREEN}backend-https${NC} 백엔드를 HTTPS로 시작
  ${GREEN}proxy${NC}         백엔드 + Nginx 프록시 시작 (인프라 포함)
  ${GREEN}frontend${NC}   프론트엔드만 시작
  ${GREEN}infra${NC}      Docker 인프라만 시작 (PostgreSQL + MinIO)
  ${GREEN}migrate${NC}    Alembic 마이그레이션만 실행
  ${GREEN}status${NC}     서비스 상태 확인
  ${GREEN}logs${NC}       서비스 로그 보기 (컨테이너 기반)

${YELLOW}예시:${NC}
  ./dev.sh start           # 전체 개발 환경 시작
  ./dev.sh backend         # 백엔드만 실행 (HTTP)
  ./dev.sh backend-https   # 백엔드를 HTTPS로 실행
  ./dev.sh status          # 현재 상태 확인

${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}
EOF
}

# 사전 검사: 필수 도구 설치 확인
check_prerequisites() {
    log_info "사전 검사 중..."
    
    # Docker 확인
    if ! command -v docker &> /dev/null; then
        log_error "Docker가 설치되어 있지 않습니다."
        log_info "설치 방법: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # Docker Compose 확인
    if ! command -v docker compose &> /dev/null && ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose가 설치되어 있지 않습니다."
        log_info "설치 방법: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    # Python3 확인
    if ! command -v python3 &> /dev/null; then
        log_error "Python3가 설치되어 있지 않습니다."
        log_info "설치 방법: https://www.python.org/downloads/"
        exit 1
    fi
    
    # Flutter 확인 (Linux 설치 경로 우선)
    FLUTTER_CMD=""
    if [ -f "$HOME/flutter-linux/bin/flutter" ]; then
        FLUTTER_CMD="$HOME/flutter-linux/bin/flutter"
        FLUTTER_AVAILABLE=true
        log_success "Linux Flutter 발견: $FLUTTER_CMD"
    elif command -v flutter &> /dev/null; then
        FLUTTER_CMD="flutter"
        FLUTTER_AVAILABLE=true
        log_success "시스템 Flutter 발견: $(which flutter)"
    else
        log_warning "Flutter가 설치되어 있지 않습니다. (프론트엔드 실행 불가)"
        log_info "설치 방법: https://docs.flutter.dev/get-started/install"
        FLUTTER_AVAILABLE=false
    fi
    
    # .env 파일 확인
    if [ ! -f "backend/.env" ]; then
        log_error "backend/.env 파일이 존재하지 않습니다."
        log_info "backend/.env.example을 복사하여 backend/.env를 생성하고 필요한 값을 설정하세요."
        exit 1
    fi
    
    log_success "사전 검사 완료"
}

# Docker 인프라 시작
start_infra() {
    log_info "Docker 인프라 시작 중... (PostgreSQL + MinIO)"
    
    docker compose up -d postgres minio minio-init
    
    log_info "PostgreSQL 준비 대기 중..."
    local count=0
    local max_wait=30
    
    while [ $count -lt $max_wait ]; do
        if docker compose exec -T postgres pg_isready -U samantha_user -d samantha_db &> /dev/null; then
            log_success "PostgreSQL 준비 완료"
            return 0
        fi
        echo -n "."
        sleep 1
        count=$((count + 1))
    done
    
    log_error "PostgreSQL 시작 시간 초과 (30초)"
    exit 1
}

# Alembic 마이그레이션 실행
run_migration() {
    log_info "데이터베이스 마이그레이션 실행 중..."
    
    cd backend
    
    # venv 활성화 확인
    if [ ! -f "$VENV_ACTIVATE" ]; then
        log_error "Python venv가 존재하지 않습니다."
        log_info "다음 명령어로 venv를 생성하세요: cd backend && python3 -m venv .venv && source $VENV_ACTIVATE && pip install -r requirements.txt"
        exit 1
    fi
    
    source "$VENV_ACTIVATE"
    alembic upgrade head
    deactivate
    
    cd ..
    log_success "마이그레이션 완료"
}

# 백엔드 시작
start_backend() {
    local use_https="${1:-false}"
    
    if [ "$use_https" = "true" ]; then
        check_ssl_certs
        log_info "백엔드 시작 중 (HTTPS 모드)..."
    else
        log_info "백엔드 시작 중 (HTTP 모드)..."
    fi
    
    # 인프라 확인
    if ! docker compose ps postgres | grep -q "Up"; then
        log_warning "인프라가 실행 중이지 않습니다. 자동으로 시작합니다."
        start_infra
    fi
    
    # 마이그레이션 실행
    run_migration
    
    cd backend
    source "$VENV_ACTIVATE"
    
    # HTTPS 모드인 경우
    if [ "$use_https" = "true" ]; then
        # HTTPS로 uvicorn 실행
        log_info "HTTPS 백엔드 서버 시작 중..."
        export FORCE_HTTPS=true
        nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 \
            --ssl-keyfile certs/localhost-key.pem \
            --ssl-certfile certs/localhost.pem > ../backend.log 2>&1 &
        local backend_pid=$!
        echo $backend_pid > ../$BACKEND_PID_FILE
        
        deactivate
        cd ..
        
        log_info "백엔드 헬스체크 대기 중..."
        local count=0
        local max_wait=30
        local backend_url="https://localhost:8000"
        
        while [ $count -lt $max_wait ]; do
            if curl -k -s "$backend_url/health" &> /dev/null; then
                log_success "HTTPS 백엔드 시작 완료 (PID: $backend_pid)"
                log_info "백엔드 URL: $backend_url"
                log_info "API 문서: $backend_url/docs"
                log_warning "⚠️  자체 서명 인증서를 사용하므로 브라우저에서 보안 경고가 표시될 수 있습니다."
                return 0
            fi
            echo -n "."
            sleep 1
            count=$((count + 1))
        done
        
        log_warning "백엔드 헬스체크 시간 초과 (30초)"
        log_info "백엔드가 시작 중일 수 있습니다. 로그를 확인하세요: ./dev.sh logs"
    else
        # HTTP로 uvicorn 실행
        nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
        local backend_pid=$!
        echo $backend_pid > ../$BACKEND_PID_FILE
        
        deactivate
        cd ..
        
        log_info "백엔드 헬스체크 대기 중..."
        local count=0
        local max_wait=30
        
        while [ $count -lt $max_wait ]; do
            if curl -s http://localhost:8000/health &> /dev/null; then
                log_success "백엔드 시작 완료 (PID: $backend_pid)"
                log_info "백엔드 URL: http://localhost:8000"
                log_info "API 문서: http://localhost:8000/docs"
                return 0
            fi
            echo -n "."
            sleep 1
            count=$((count + 1))
        done
        
        log_warning "백엔드 헬스체크 시간 초과 (30초)"
        log_info "백엔드가 시작 중일 수 있습니다. 로그를 확인하세요: ./dev.sh logs"
    fi
}

# 프론트엔드 시작
start_frontend() {
    if [ "$FLUTTER_AVAILABLE" = false ]; then
        log_error "Flutter가 설치되어 있지 않아 프론트엔드를 시작할 수 없습니다."
        return 1
    fi
    
    # 기존 Flutter 프로세스 완전 정리
    log_info "기존 Flutter 프로세스 정리 중..."
    pkill -f "flutter run" 2>/dev/null || true
    
    # 포트 8080이 이미 사용 중인지 확인
    if lsof -i :8080 &> /dev/null || ss -tuln 2>/dev/null | grep -q ":8080 " || netstat -tuln 2>/dev/null | grep -q ":8080 "; then
        log_warning "포트 8080이 이미 사용 중입니다. 기존 프로세스를 종료합니다."
        # 포트 8080을 사용하는 프로세스 종료
        local port_pid=$(lsof -t -i:8080 2>/dev/null || true)
        if [ -n "$port_pid" ]; then
            kill -15 $port_pid 2>/dev/null || true
            sleep 2
            kill -9 $port_pid 2>/dev/null || true
            sleep 1
        fi
    fi
    
    # PID 파일 정리
    if [ -f "$FRONTEND_PID_FILE" ]; then
        local old_pid=$(cat "$FRONTEND_PID_FILE" 2>/dev/null || true)
        if [ -n "$old_pid" ] && kill -0 "$old_pid" 2>/dev/null; then
            log_warning "기존 프론트엔드 프로세스 정리 (PID: $old_pid)"
            kill -15 "$old_pid" 2>/dev/null || true
            sleep 2
            kill -9 "$old_pid" 2>/dev/null || true
        fi
        rm -f "$FRONTEND_PID_FILE"
    fi
    
    log_info "프론트엔드 시작 중..."
    
    # frontend 디렉토리로 이동
    cd frontend
    
    # 의존성 설치
    log_info "Flutter 의존성 설치 중..."
    $FLUTTER_CMD pub get
    
    # 백그라운드로 Flutter 웹 앱 실행 (브라우저 자동 열기는 Flutter가 처리)
    log_info "Flutter 웹 앱 실행 중..."
    nohup $FLUTTER_CMD run -d chrome --web-port 8080 > ../frontend.log 2>&1 &
    local frontend_pid=$!
    echo $frontend_pid > ../$FRONTEND_PID_FILE
    
    cd ..
    
    # 프론트엔드 시작 대기
    log_info "프론트엔드 시작 대기 중..."
    local count=0
    local max_wait=60  # Flutter는 더 오래 걸릴 수 있음
    
    while [ $count -lt $max_wait ]; do
        if curl -s http://localhost:8080 &> /dev/null; then
            log_success "프론트엔드 시작 완료 (PID: $frontend_pid)"
            log_info "프론트엔드 URL: http://localhost:8080"
            log_info "Flutter가 자동으로 브라우저를 열었습니다."
            return 0
        fi
        echo -n "."
        sleep 2
        count=$((count + 2))
    done
    
    log_warning "프론트엔드 헬스체크 시간 초과 (60초)"
    log_info "프론트엔드가 시작 중일 수 있습니다. 로그를 확인하세요: tail -f frontend.log"
}

# SSL 인증서 확인 및 생성
check_ssl_certs() {
    log_info "SSL 인증서 상태 확인 중..."
    
    # 인증서 파일들이 모두 존재하는지 확인
    if [ -f "backend/certs/localhost.pem" ] && \
       [ -f "backend/certs/localhost-key.pem" ] && \
       [ -f "frontend/localhost.pem" ] && \
       [ -f "frontend/localhost-key.pem" ]; then
        log_success "SSL 인증서가 이미 존재합니다. (생성 건너뜀)"
        return 0
    fi
    
    log_warning "SSL 인증서가 없거나 일부 누락되었습니다."
    log_info "인증서를 새로 생성합니다..."
    
    # backend/certs 디렉토리가 없으면 생성, 있으면 권한 보정
    if [ ! -d "backend/certs" ]; then
        mkdir -p backend/certs
    fi
    chmod 755 backend/certs
    
    # generate_certs.sh 실행
    cd backend/certs
    if [ -f "./generate_certs.sh" ]; then
        bash ./generate_certs.sh
    else
        log_error "generate_certs.sh 스크립트를 찾을 수 없습니다."
        cd ../..
        exit 1
    fi
    cd ../..
}

# 전체 시작 (컨테이너 기반)
start_all() {
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "🚀 Samantha 개발 환경 전체 시작 (컨테이너 기반)"
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # 이미 실행 중인지 확인
    if docker compose ps -q | grep -q .; then
        log_warning "개발 환경이 이미 실행 중입니다."
        log_info "현재 상태를 확인하려면: ./dev.sh status"
        log_info "기존 환경을 중지하려면: ./dev.sh stop"
        return 0
    fi
    
    # SSL 인증서 확인
    check_ssl_certs
    
    # Docker Compose로 모든 서비스 시작
    log_info "모든 서비스 컨테이너 시작 중..."
    docker compose up -d --build
    
    # 서비스 헬스체크
    log_info "서비스 상태 확인 중..."
    local max_wait=120
    local count=0
    
    while [ $count -lt $max_wait ]; do
        local backend_ready=false
        local frontend_ready=false
        
        # 백엔드 헬스체크 (HTTPS)
        if curl -k -s https://localhost:8000/health &> /dev/null; then
            backend_ready=true
        fi
        
        # 프론트엔드 헬스체크 (HTTPS 200 응답)
        if curl -k -s -o /dev/null -w "%{http_code}" https://localhost:8443 | grep -q "200"; then
            frontend_ready=true
        fi
        
        if [ "$backend_ready" = true ] && [ "$frontend_ready" = true ]; then
            echo ""
            log_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            log_success "✨ 전체 개발 환경 시작 완료!"
            log_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo ""
            log_info "🌐 백엔드: https://localhost:8000"
            log_info "🌐 프론트엔드: https://localhost:8443"
            log_info "📚 API 문서: https://localhost:8000/docs"
            echo ""
            log_info "📊 서비스 상태 확인: ./dev.sh status"
            log_info "📝 서비스 로그 보기: ./dev.sh logs [서비스명]"
            log_info "🛑 전체 중지: ./dev.sh stop"
            
            # 브라우저에서 자동으로 열기
            if command -v xdg-open &> /dev/null; then
                log_info "🌐 브라우저에서 프론트엔드 열기 중..."
                sleep 2  # 컨테이너가 완전히 준비될 때까지 대기
                xdg-open https://localhost:8443 &> /dev/null &
                log_info "💡 브라우저가 자동으로 열리지 않으면 수동으로 접속해주세요: https://localhost:8443"
            elif command -v wslview &> /dev/null; then
                log_info "🌐 Windows 브라우저에서 프론트엔드 열기 중..."
                sleep 2
                wslview https://localhost:8443 &> /dev/null &
                log_info "💡 브라우저가 자동으로 열리지 않으면 수동으로 접속해주세요: https://localhost:8443"
            fi
            
            return 0
        fi
        
        echo -n "."
        sleep 2
        count=$((count + 2))
    done
    
    echo ""
    log_warning "서비스 시작 시간 초과 (120초)"
    log_info "컨테이너 상태를 확인하세요: docker compose ps"
    log_info "로그를 확인하세요: docker compose logs"
}

# 전체 중지 (컨테이너 기반)
stop_all() {
    log_info "전체 서비스 중지 중..."
    
    # Docker Compose로 모든 서비스 중지
    docker compose down
    log_success "모든 컨테이너 중지 완료 (볼륨 유지)"
    
    # 잔여 프로세스 정리 (혹시 남아있을 수 있는 로컬 프로세스들)
    log_info "잔여 프로세스 정리 중..."
    
    # 혹시 남아있을 수 있는 로컬 프로세스들 정리
    pkill -f "uvicorn app.main:app" 2>/dev/null && log_success "잔여 백엔드 프로세스 종료" || true
    pkill -f "flutter run" 2>/dev/null && log_success "잔여 Flutter 프로세스 종료" || true
    pkill -f "dart.*flutter_tools" 2>/dev/null && log_success "Dart 도구 프로세스 종료" || true
    
    # 포트 정리
    for port in 8000 8080; do
        if lsof -i :$port &> /dev/null; then
            local port_pids=$(lsof -t -i:$port 2>/dev/null || true)
            if [ -n "$port_pids" ]; then
                echo "$port_pids" | xargs -r kill -15 2>/dev/null || true
                sleep 2
                echo "$port_pids" | xargs -r kill -9 2>/dev/null || true
                log_success "포트 $port 점유 프로세스 정리 완료"
            fi
        fi
    done
    
    # PID 파일들 정리
    rm -f "$FRONTEND_PID_FILE" "$BACKEND_PID_FILE" 2>/dev/null || true
    
    log_success "전체 중지 완료"
}

# 상태 확인 (컨테이너 기반)
check_status() {
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "📊 Samantha 개발 환경 상태 (컨테이너 기반)"
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Docker Compose 서비스 상태 확인
    if ! docker compose ps --quiet | grep -q .; then
        log_warning "현재 실행 중인 서비스가 없습니다."
        log_info "서비스를 시작하려면: ./dev.sh start"
        return 1
    fi
    
    echo "🐳 컨테이너 상태:"
    docker compose ps --format "table {{.Name}}\t{{.State}}\t{{.Status}}\t{{.Ports}}"
    
    echo ""
    echo "🌐 서비스 접속 URL:"
    
    # 각 서비스 접근 가능 여부 확인
    if curl -k -s https://localhost:8000/health &> /dev/null; then
        log_success "✅ 백엔드: https://localhost:8000"
        log_info "   📚 API 문서: https://localhost:8000/docs"
    else
        log_warning "❌ 백엔드: https://localhost:8000 (응답 없음)"
    fi
    
    if curl -k -s -o /dev/null -w "%{http_code}" https://localhost:8443 | grep -q "200"; then
        log_success "✅ 프론트엔드: https://localhost:8443"
    else
        log_warning "❌ 프론트엔드: https://localhost:8443 (응답 없음)"
    fi
    
    echo ""
    echo "💾 리소스 사용량:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
    log_info "📊 서비스 상태 확인"
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    echo ""
    echo -e "${YELLOW}[Docker 서비스]${NC}"
    docker compose ps
    
    echo ""
    echo -e "${YELLOW}[백엔드 프로세스]${NC}"
    if [ -f "$BACKEND_PID_FILE" ]; then
        local pid=$(cat $BACKEND_PID_FILE)
        if ps -p $pid > /dev/null 2>&1; then
            echo -e "${GREEN}✅ 실행 중 (PID: $pid)${NC}"
        else
            echo -e "${RED}❌ 중지됨 (PID 파일은 존재하지만 프로세스 없음)${NC}"
        fi
    else
        if pgrep -f "uvicorn app.main:app" > /dev/null; then
            local pid=$(pgrep -f "uvicorn app.main:app")
            echo -e "${YELLOW}⚠️  실행 중이지만 PID 파일 없음 (PID: $pid)${NC}"
        else
            echo -e "${RED}❌ 중지됨${NC}"
        fi
    fi
    
    echo ""
    echo -e "${YELLOW}[프론트엔드 프로세스]${NC}"
    if [ -f "$FRONTEND_PID_FILE" ]; then
        local pid=$(cat $FRONTEND_PID_FILE)
        if ps -p $pid > /dev/null 2>&1; then
            echo -e "${GREEN}✅ 실행 중 (PID: $pid)${NC}"
        else
            echo -e "${RED}❌ 중지됨 (PID 파일은 존재하지만 프로세스 없음)${NC}"
        fi
    else
        if pgrep -f "flutter run" > /dev/null; then
            local pid=$(pgrep -f "flutter run")
            echo -e "${YELLOW}⚠️  실행 중이지만 PID 파일 없음 (PID: $pid)${NC}"
        else
            echo -e "${RED}❌ 중지됨${NC}"
        fi
    fi
    
    echo ""
    echo -e "${YELLOW}[포트 사용 확인]${NC}"
    echo -n "  8000 (백엔드):   "
    if lsof -i :8000 &> /dev/null || ss -tuln 2>/dev/null | grep -q ":8000 " || netstat -tuln 2>/dev/null | grep -q ":8000 "; then
        echo -e "${GREEN}✅ 사용 중${NC}"
    else
        echo -e "${RED}❌ 미사용${NC}"
    fi
    
    echo -n "  5432 (PostgreSQL): "
    if lsof -i :5432 &> /dev/null || ss -tuln 2>/dev/null | grep -q ":5432 " || netstat -tuln 2>/dev/null | grep -q ":5432 "; then
        echo -e "${GREEN}✅ 사용 중${NC}"
    else
        echo -e "${RED}❌ 미사용${NC}"
    fi
    
    echo -n "  9005 (MinIO):    "
    if lsof -i :9005 &> /dev/null || ss -tuln 2>/dev/null | grep -q ":9005 " || netstat -tuln 2>/dev/null | grep -q ":9005 "; then
        echo -e "${GREEN}✅ 사용 중${NC}"
    else
        echo -e "${RED}❌ 미사용${NC}"
    fi
    
    echo -n "  8443 (프론트엔드):  "
    if lsof -i :8443 &> /dev/null || ss -tuln 2>/dev/null | grep -q ":8443 " || netstat -tuln 2>/dev/null | grep -q ":8443 "; then
        echo -e "${GREEN}✅ 사용 중${NC}"
    else
        echo -e "${RED}❌ 미사용${NC}"
    fi

    
    echo ""
    echo -e "${YELLOW}[헬스체크]${NC}"
    echo -n "  백엔드 (8000):    "
    if curl -k -s https://localhost:8000/health &> /dev/null; then
        echo -e "${GREEN}✅ 정상${NC}"
    else
        echo -e "${RED}❌ 응답 없음${NC}"
    fi
    
    echo -n "  프론트엔드 (8443): "
    if curl -k -s https://localhost:8443 &> /dev/null; then
        echo -e "${GREEN}✅ 정상${NC}"
    else
        echo -e "${RED}❌ 응답 없음${NC}"
    fi
    
    echo ""
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# 로그 보기
show_logs() {
    local service="$1"
    
    if [ -z "$service" ]; then
        log_info "📝 사용 가능한 서비스 로그:"
        echo "  • backend     - 백엔드 서비스 로그"
        echo "  • frontend    - 프론트엔드 서비스 로그"
        echo "  • postgres    - PostgreSQL 데이터베이스 로그"
        echo "  • minio       - MinIO 객체 스토리지 로그"
        echo ""
        log_info "사용법: ./dev.sh logs [서비스명]"
        log_info "전체 로그: docker compose logs -f"
        return 0
    fi
    
    # 서비스가 실행 중인지 확인
    if ! docker compose ps --quiet "$service" | grep -q .; then
        log_error "서비스 '$service'가 실행 중이지 않습니다."
        log_info "실행 중인 서비스 확인: ./dev.sh status"
        return 1
    fi
    
    log_info "$service 서비스 로그 (Ctrl+C로 종료):"
    docker compose logs -f "$service"
}

# 백엔드 + 프록시 시작
start_proxy() {
    log_info "백엔드 및 Nginx 프록시 시작 중..."
    
    # SSL 인증서 확인
    check_ssl_certs
    
    # 필요한 서비스만 선택적으로 시작 (인프라 포함, redis 제외)
    docker compose up -d postgres minio minio-init backend nginx
    
    log_info "서비스 헬스체크 중..."
    local count=0
    local max_wait=30
    
    while [ $count -lt $max_wait ]; do
        # Nginx를 통한 백엔드 헬스체크 (포트 8000)
        if curl -k -s https://localhost:8000/health &> /dev/null; then
            echo ""
            log_success "백엔드 및 프록시 시작 완료"
            log_info "백엔드(Nginx 프록시): https://localhost:8000"
            log_info "API 문서: https://localhost:8000/docs"
            return 0
        fi
        echo -n "."
        sleep 1
        count=$((count + 1))
    done
    
    echo ""
    log_warning "헬스체크 시간 초과"
}

# 메인 로직
case "${1:-}" in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    clean)
        log_warning "데이터 볼륨을 포함하여 전체 서비스를 삭제합니다."
        docker compose down --volumes
        rm -f "$FRONTEND_PID_FILE" "$BACKEND_PID_FILE" 2>/dev/null || true
        log_success "볼륨 삭제 완료"
        ;;
    backend)
        check_prerequisites
        start_backend false
        ;;
    backend-https)
        check_prerequisites
        start_backend true
        ;;
    proxy)
        check_prerequisites
        start_proxy
        ;;
    frontend)
        check_prerequisites
        start_frontend
        ;;
    infra)
        check_prerequisites
        start_infra
        log_success "인프라 시작 완료"
        docker compose ps
        ;;
    migrate)
        check_prerequisites
        run_migration
        ;;
    status)
        check_status
        ;;
    logs)
        show_logs "$2"
        ;;
    *)
        usage
        exit 1
        ;;
esac
