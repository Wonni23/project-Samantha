import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlmodel import SQLModel

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

# ----------------------------------------------------------------
# [커스텀 설정] 프로젝트 경로를 잡아줘야 app 모듈을 찾을 수 있습니다.
# ----------------------------------------------------------------
sys.path.append(os.getcwd())

# 1. 우리의 모델들을 전부 로딩합니다. (STEP 1에서 만든 파일)
# 이걸 안 하면 "No changes detected"라며 테이블이 안 만들어집니다.
from app.models import * # noqa
from app.core.config import settings # 환경변수(DB URL) 가져오기

# 2. Alembic 설정 객체
config = context.config

# 3. 로깅 설정
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# [핵심 트릭]
# FastAPI는 'asyncpg'를 쓰지만, Alembic은 'psycopg2'(동기)를 써야 합니다.
# 따라서 URL에 '+asyncpg'가 있다면 제거해서 순수 postgresql URL로 변환합니다.
db_url = settings.DATABASE_URL
if db_url and "postgresql+asyncpg" in db_url:
    db_url = db_url.replace("postgresql+asyncpg", "postgresql")

config.set_main_option("sqlalchemy.url", db_url)

# 5. SQLModel의 메타데이터를 Alembic에게 전달
target_metadata = SQLModel.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
