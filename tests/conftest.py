import pytest
from unittest.mock import AsyncMock

from database.mongo import MongoDatabase
from database.postgres import PostgresDatabase

# ------ FIXTURE MONGO DATABASE ------
@pytest.fixture
async def mongo_fixture():
    """
    Fixture que prepara una instancia de MongoDatabase para los tests.
    Usa mocks para evitar conexión real a MongoDB.
    """
    # Simulamos el cliente y la base de datos
    mock_client = AsyncMock()
    mock_db = AsyncMock()

    # Creamos instancia del objeto real pero sustituimos sus atributos internos
    mongo = MongoDatabase(mongo_uri="mongodb://fake_uri", mongo_db_name="test_db")
    mongo._client = mock_client
    mongo._db = mock_db

    yield mongo  # Entrega la instancia al test

    # Limpieza posterior
    await mongo.close()

# ------ FIXTURE POSTGRES DATABASE ------
@pytest.fixture
async def postgres_fixture():
    """
    Fixture que prepara una instancia de PostgresDatabase con mocks,
    sin necesidad de conectar a una base de datos real.
    """
    db = PostgresDatabase(
        user="user",
        password="pass",
        host="localhost",
        database="test_db",
    )

    # Creamos un mock para el pool y sus métodos
    mock_pool = AsyncMock()
    db._pool = mock_pool

    yield db

    await db.close()