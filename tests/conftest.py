import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Intent


@pytest.fixture
def client():
    """Provide an isolated in-memory database and FastAPI test client per test."""
    # Share one in-memory SQLite connection across the test client's request threads.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)

    # Seed the same intent catalog that the production Alembic migration creates.
    with TestingSession() as database:
        database.add_all(
            [
                Intent(name="duvida", description="Perguntas gerais."),
                Intent(name="reclamacao", description="Reclamações."),
                Intent(name="suporte", description="Suporte técnico."),
                Intent(name="financeiro", description="Assuntos financeiros."),
                Intent(name="vendas", description="Vendas."),
                Intent(name="cancelamento", description="Cancelamentos."),
                Intent(name="outros", description="Outros assuntos."),
            ]
        )
        database.commit()

    # Route every request to the isolated test database instead of PostgreSQL.
    def override_get_db():
        with TestingSession() as database:
            yield database

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client

    # Remove dependency overrides and release the temporary database after the test.
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()