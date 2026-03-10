import logging
import aioboto3
from botocore.exceptions import ClientError
from app.core.config import settings
import uuid
from datetime import datetime
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self):
        self.session = aioboto3.Session()

        # S3 연결 설정
        self.s3_config = {
            "service_name": "s3",
            "endpoint_url": settings.S3_ENDPOINT_URL,
            "aws_access_key_id": settings.S3_ACCESS_KEY,
            "aws_secret_access_key": settings.S3_SECRET_KEY,
        }
        self.bucket_name = settings.S3_BUCKET_NAME

    async def upload_bytes(self, data: bytes, folder: str, filename: str = None) -> str:
        """
        바이너리 데이터를 S3에 업로드하고 URL을 반환합니다.
        """
        if not filename:
            ext = ".webm"
            filename = f"{uuid.uuid4()}{ext}"

        # S3 키(경로) 생성: voice_inputs/20240128/uuid.webm
        today = datetime.now().strftime("%Y%m%d")
        object_key = f"{folder}/{today}/{filename}"

        try:
            async with self.session.client(**self.s3_config) as s3:
                # 1. 파일 업로드
                await s3.put_object(
                    Bucket=self.bucket_name,
                    Key=object_key,
                    Body=data,
                    ContentType="audio/webm"
                )

                # [개선] URL 파싱을 사용하여 hostname을 정확히 확인 (보안 강화)
                parsed_endpoint = urlparse(settings.S3_ENDPOINT_URL)
                hostname = parsed_endpoint.hostname
                if hostname and hostname in ["localhost", "127.0.0.1"]:
                    url = f"{settings.S3_ENDPOINT_URL}/{self.bucket_name}/{object_key}"
                else:
                    url = f"https://{self.bucket_name}.s3.amazonaws.com/{object_key}"
                logger.info("[Storage] Upload success: %s", object_key)
                return url

        except ClientError as e:
            logger.error("[Storage] Upload failed (ClientError): %s", e)
            raise
        except Exception as e:
            logger.error("[Storage] Upload failed (unexpected): %s", e)
            raise

    async def delete_file(self, file_url: str) -> bool:
        """
        S3 URL에서 파일 경로(Key)를 추출하여 해당 파일을 삭제합니다.
        성공 시 True를 반환하며, 실패 시 에러 로그를 남기고 False를 반환합니다.
        """
        if not file_url:
            return False

        try:
            # URL에서 Object Key 추출 (path-style / virtual-hosted-style 모두 대응)
            parsed = urlparse(file_url)
            path = parsed.path.lstrip("/")
            hostname = parsed.hostname or ""

            if f"{self.bucket_name}/" in path:
                # path-style: http://endpoint/bucket/folder/key
                object_key = path.split(f"{self.bucket_name}/", 1)[-1]
            elif hostname.startswith(f"{self.bucket_name}."):
                # virtual-hosted-style: https://bucket.s3.amazonaws.com/folder/key
                object_key = path
            else:
                logger.warning("[Storage] Invalid URL format for deletion: %s", file_url)
                return False

            # 2. S3 클라이언트를 통한 삭제 실행
            async with self.session.client(**self.s3_config) as s3:
                await s3.delete_object(
                    Bucket=self.bucket_name,
                    Key=object_key
                )

                logger.info("[Storage] Delete success: %s", object_key)
                return True

        except ClientError as e:
            logger.error("[Storage] Delete failed — orphan key: %s, error: %s", file_url, e)
            return False
        except Exception as e:
            logger.error("[Storage] Delete failed — orphan key: %s, error: %s", file_url, e)
            return False


# 전역 인스턴스
s3_uploader = StorageService()
