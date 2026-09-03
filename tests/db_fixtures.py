import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.database import Base
import app.models  # noqa: F401 — register all ORM models

# Use a local SQLite test database so tests run 100% offline without network
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_sentriq.db"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session", autouse=True)
async def setup_test_database():
    """Create all tables before test session and clean up after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture
async def db_session() -> AsyncSession:
    """Yield an async database session for each test."""
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.rollback()
        finally:
            await session.close()
