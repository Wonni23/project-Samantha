#!/bin/bash

# SSL 인증서 생성 스크립트 (개발용)
# 사용법: ./generate_certs.sh

set -e

# 색상 정의
GREEN=$'\033[0;32m'
RED=$'\033[0;31m'
YELLOW=$'\033[1;33m'
BLUE=$'\033[0;34m'
NC=$'\033[0m' # No Color

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

# 인증서 디렉토리 생성
CERT_DIR="$(dirname "$0")"
cd "$CERT_DIR"

log_info "개발용 SSL 인증서 생성 시작..."

# 기존 인증서 백업
if [ -f "localhost.pem" ] || [ -f "localhost-key.pem" ]; then
    log_warning "기존 인증서를 발견했습니다. 백업 중..."
    mkdir -p backup
    cp -f localhost*.pem backup/ 2>/dev/null || true
    log_success "기존 인증서 백업 완료"
fi

# mkcert 확인 (Windows/Linux)
MKCERT_CMD=""
if command -v mkcert.exe &> /dev/null; then
    MKCERT_CMD="mkcert.exe"
elif command -v mkcert &> /dev/null; then
    MKCERT_CMD="mkcert"
fi

if [ -n "$MKCERT_CMD" ]; then
    log_info "mkcert($MKCERT_CMD)가 감지되었습니다. 신뢰할 수 있는 로컬 인증서를 생성합니다."
    
    # Root CA 설치 (최초 1회)
    $MKCERT_CMD -install
    
    # 인증서 생성
    log_info "localhost 인증서 생성 중..."
    $MKCERT_CMD -key-file localhost-key.pem -cert-file localhost.pem localhost 127.0.0.1 ::1
    
    log_success "✨ mkcert로 신뢰할 수 있는 인증서 생성 완료!"
    
else
    log_warning "mkcert를 찾을 수 없습니다. OpenSSL로 자체 서명 인증서를 생성합니다."
    log_info "브라우저에서 '주의 요함' 경고를 없애려면 Windows에 mkcert를 설치하세요."
    
    # OpenSSL 설정 파일 생성
    cat > localhost.conf << EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req

[dn]
C=KR
ST=Seoul
L=Seoul
O=Samantha Development
OU=Development Team
CN=localhost

[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = *.localhost
IP.1 = 127.0.0.1
IP.2 = ::1
EOF

    # 개인키 생성
    log_info "개인키 생성 중..."
    openssl genrsa -out localhost-key.pem 2048

    # 인증서 서명 요청(CSR) 생성
    log_info "인증서 서명 요청 생성 중..."
    openssl req -new -key localhost-key.pem -out localhost.csr -config localhost.conf

    # 자체 서명 인증서 생성
    log_info "자체 서명 인증서 생성 중..."
    openssl x509 -req -in localhost.csr -signkey localhost-key.pem -out localhost.pem -days 365 -extensions v3_req -extfile localhost.conf

    # 정리
    rm localhost.csr localhost.conf
fi

# 권한 설정
if [ -f "localhost-key.pem" ]; then
    chmod 600 localhost-key.pem
fi
if [ -f "localhost.pem" ]; then
    chmod 644 localhost.pem
fi

log_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_success "✨ 개발용 SSL 인증서 생성 완료!"
log_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
log_info "📄 생성된 파일:"
log_info "  • localhost.pem (인증서)"
log_info "  • localhost-key.pem (개인키)"
echo ""

log_warning "⚠️  브라우저 보안 경고 해결 방법:"
log_info "1. Chrome에서 https://localhost:8000 접속"
log_info "2. '고급' 클릭 후 '안전하지 않음(localhost)(으)로 이동' 클릭"
log_info "3. 또는 Chrome에서 chrome://flags/#allow-insecure-localhost 활성화"
echo ""

log_info "🔧 인증서 정보 확인:"
log_info "openssl x509 -in localhost.pem -text -noout"
echo ""

log_success "이제 HTTPS 개발 서버를 시작할 수 있습니다!"

# 프론트엔드로 인증서 복사 (Nginx용)
if [ -d "../../frontend" ]; then
    log_info "프론트엔드 디렉토리로 인증서 복사 중..."
    cp localhost.pem ../../frontend/
    cp localhost-key.pem ../../frontend/
    log_success "프론트엔드 인증서 동기화 완료"
else
    log_warning "프론트엔드 디렉토리를 찾을 수 없습니다 (../../frontend). 복사 건너뜀."
fi