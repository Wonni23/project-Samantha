# ./frontend/nginx.conf

server {
    listen 80;
    server_name _; # 어떤 요청이든 묻지도 따지지도 않고 처리 (대문에서 이미 필터링 됨)

    root /usr/share/nginx/html;
    index index.html;

    # 백엔드 관련 proxy_pass 전부 삭제! (호스트 Nginx가 대신 해줌)

    # Flutter SPA 라우팅
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 정적 파일 캐싱 최적화
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}