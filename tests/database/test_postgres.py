import pytest
from unittest.mock import patch, AsyncMock

from src.database.postgres import PostgresDatabase

# ------ TESTS UNITARIOS ------
def test_build_dsn_without_ssl():
    """ ✅ Test para la construcción del DSN sin SSL. Por defecto. Sin mocks."""
    dsn = PostgresDatabase._build_dsn("user", "pass", "localhost", 5432, "db_name", ssl=False)
    assert dsn == "postgresql://user:pass@localhost:5432/db_name"

def test_build_dsn_with_ssl():
    """ ✅ Test para la construcción del DSN con SSL. Por defecto. Sin mocks."""
    dsn = PostgresDatabase._build_dsn("user", "pass", "localhost", 5432, "db_name", ssl=True)
    assert dsn.endswith("?sslmode=require")

@pytest.mark.asyncio
async def test_connect_creates_pool():
    """ ✅ Test para verificar que connect crea el pool de conexiones."""
    # Reemplazamos la llamada real a asyncpg.create_pool por un mock
    with patch("src.database.postgres.asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool:
        db = PostgresDatabase(user="u", password="p", database="d")
        await db.connect()
        mock_create_pool.assert_awaited_once()
        assert db._pool is not None

@pytest.mark.asyncio
async def test_connect_does_not_recreate_pool(postgres_fixture):
    """ ✅ Test para verificar que connect no recrea el pool si ya existe."""
    postgres_fixture._pool = AsyncMock()  # El mock del pool ya existe
    with patch("src.database.postgres.asyncpg.create_pool", new_callable=AsyncMock) as mock_create_pool:
        await postgres_fixture.connect()
        mock_create_pool.assert_not_awaited()

@pytest.mark.asyncio
async def test_ping_returns_true(postgres_fixture):
    """ ✅ Test para verificar que ping devuelve True cuando la conexión es exitosa."""
    mock_conn = AsyncMock()
    mock_conn.fetchval.return_value = 1 # Simulamos que la consulta devuelve 1 (éxito)
    postgres_fixture._pool.acquire = AsyncMock(return_value=mock_conn) # Mock del acquire para tomar una conexión simulada
    postgres_fixture._pool.release = AsyncMock() # Mock del release para devolver la conexión simulada

    result = await postgres_fixture.ping()
    assert result is True
    mock_conn.fetchval.assert_awaited_once_with("SELECT 1;") # Verificamos que se llamó a la consulta

@pytest.mark.asyncio
async def test_ensure_pool_raises_when_uninitialized():
    """ ✅ Test para verificar que _ensure_pool lanza RuntimeError si el pool no está inicializado."""
    db = PostgresDatabase(user="u", password="p", database="d")
    with pytest.raises(RuntimeError, match="Connection pool not initialized"):
        await db._ensure_pool()

@pytest.mark.asyncio
async def test_execute_runs_query(postgres_fixture):
    """ ✅ Test para verificar que execute ejecuta una consulta correctamente."""
    mock_conn = AsyncMock()
    postgres_fixture._pool.acquire = AsyncMock(return_value=mock_conn)
    postgres_fixture._pool.release = AsyncMock()

    await postgres_fixture.execute("INSERT INTO table VALUES ($1)", 123) # Ejecutamos la consulta de prueba
    mock_conn.execute.assert_awaited_once_with("INSERT INTO table VALUES ($1)", 123)

@pytest.mark.asyncio
async def test_fetch_methods(postgres_fixture):
    """ ✅ Test para verificar que los métodos fetch_one, fetch_all y fetch_val funcionan correctamente."""
    mock_conn = AsyncMock()
    postgres_fixture._pool.acquire = AsyncMock(return_value=mock_conn)
    postgres_fixture._pool.release = AsyncMock()

    await postgres_fixture.fetch_one("SELECT * FROM test WHERE id=$1", 1)
    mock_conn.fetchrow.assert_awaited_once()

    await postgres_fixture.fetch_all("SELECT * FROM test")
    mock_conn.fetch.assert_awaited_once()

    await postgres_fixture.fetch_val("SELECT COUNT(*) FROM test")
    mock_conn.fetchval.assert_awaited_once()

@pytest.mark.asyncio
async def test_create_extension_calls_execute(postgres_fixture):
    """ ✅ Test para verificar que create_extension llama a execute con la consulta correcta."""
    postgres_fixture.execute = AsyncMock()
    await postgres_fixture.create_extension("uuid-ossp")
    postgres_fixture.execute.assert_awaited_once_with("CREATE EXTENSION IF NOT EXISTS uuid-ossp;")