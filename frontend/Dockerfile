# Flutter 웹 앱 빌드를 위한 멀티스테이지 Dockerfile

# ============================================
# 1단계: Flutter 빌드 스테이지
# (보안 강화를 위해 stable 대신 특정 버전 명시)
# ============================================
# FROM ghcr.io/cirruslabs/flutter:3.38.8 AS builder

# WORKDIR /app

# Flutter 의존성 파일 복사 및 패키지 다운로드
# COPY pubspec.yaml pubspec.lock ./
# RUN flutter pub get

# 소스 코드 복사
# COPY . .

# Flutter 웹 앱 빌드 (릴리즈 모드 - 최적화됨)
# 릴리즈 모드는 프로덕션용으로 최적화되고 빌드 시간이 단축됩니다
# RUN flutter build web --release

# ============================================
# 2단계: Nginx 배포 스테이지
# ============================================
FROM nginx:alpine

# 빌드된 웹 앱을 nginx 웹 루트로 복사
COPY /web /usr/share/nginx/html

# Nginx 설정 파일 복사
COPY nginx.conf /etc/nginx/conf.d/default.conf

# HTTP 및 HTTPS 포트 노출
EXPOSE 80 443

# Nginx 실행
CMD ["nginx", "-g", "daemon off;"]
