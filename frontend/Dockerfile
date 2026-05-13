# 스테이지 구분 없이 오직 서빙만 담당하는 경량 Nginx
FROM nginx:alpine

# 로컬에서 빌드된 결과물을 컨테이너 내부로 복사
# (Dockerfile과 같은 위치에 web/ 폴더가 있어야 함)
COPY web/ /usr/share/nginx/html

# 이전에 작성한 Nginx 설정 파일 복사
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
