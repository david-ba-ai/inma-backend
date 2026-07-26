import pytest
from unittest.mock import AsyncMock, patch
from src.database.mongo import MongoDatabase, COLLECTIONS


# ------ TESTS UNITARIOS ------
@pytest.mark.asyncio
async def test_init_sets_default_uri():
    """ ✅ Test para verificar que la inicialización de MongoDatabase por defecto sin mocks"""
    mongo = MongoDatabase()
    assert mongo._client is not None
    assert mongo._db.name == "mongo_db"
    assert "users" in mongo._collections

@pytest.mark.asyncio
async def test_init_beanie_registers_models(mongo_fixture):
    """ ✅ Test para verificar que init_beanie registra los modelos correctamente """
    with patch("src.database.mongo.init_beanie", new_callable=AsyncMock) as mock_init:
        await mongo_fixture.init_beanie()
        mock_init.assert_awaited_once()

@pytest.mark.asyncio
async def test_ping_calls_admin_command(mongo_fixture):
    """ ✅ Test para verificar que el método ping llama al comando admin 'ping' """
    mongo_fixture._client.admin.command = AsyncMock()
    await mongo_fixture.ping()
    mongo_fixture._client.admin.command.assert_awaited_once_with("ping")

def test_get_collection_returns_valid(mongo_fixture):
    """ ✅ Test para verificar que get_collection devuelve la colección correcta """
    mongo_fixture._db.__getitem__.return_value = "fake_collection"
    collection = mongo_fixture.get_collection("users")
    assert collection == "fake_collection"

def test_get_collection_invalid_raises(mongo_fixture):
    """ ✅ Test para verificar que get_collection lanza ValueError para colección inválida """
    with pytest.raises(ValueError):
        mongo_fixture.get_collection("invalid_name")

@pytest.mark.asyncio
async def test_drop_all_collections_calls_drop(mongo_fixture):
    """ ✅ Test para verificar que drop_all_collections elimina todas las colecciones """
    mongo_fixture._db.list_collection_names = AsyncMock(return_value=COLLECTIONS)
    mongo_fixture._db.__getitem__.return_value.drop = AsyncMock()
    await mongo_fixture.drop_all_collections()
    mongo_fixture._db.__getitem__.return_value.drop.assert_awaited()