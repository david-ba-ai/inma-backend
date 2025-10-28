"""
Clase para manejar la conexión a MongoDB usando Beanie y Motor.
En dev, usa MONGO_HOST y MONGO_PORT sin autenticación.
Colecciones actuales: messages, users.
"""
from typing import List
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional

from src.models.messages import MessagesModel
from src.models.user import UserModel

class MongoDatabase:

    # ------INICIALIZACIÓN DE MONGO------
    def __init__(
        self,
        mongo_uri: Optional[str] = None,
        mongo_db_name: str = "mongo_db"
    ):
        """Inicializa la conexión a MongoDB"""
        # Dev sin auth
        if not mongo_uri:
            host = "mongo"
            port = "27017"
            mongo_uri = f"mongodb://{host}:{port}"

        self._client: AsyncIOMotorClient = AsyncIOMotorClient(mongo_uri)
        self._db: AsyncIOMotorDatabase = self._client[mongo_db_name]
        self._collections: List[str] = ["messages", "users"]

    # ------INICIALIZACIÓN DE BEANIE------
    async def init_beanie(self):
        """Inicializa Beanie y registra los modelos. Crea los índices si están definidos en los modelos."""
        await init_beanie(
            database=self._db,
            document_models=[MessagesModel, UserModel]
        )

    # ------VERIFICACIÓN DE LA CONEXIÓN------
    async def ping(self) -> bool:
        """Verifica la conexión a MongoDB."""
        await self._client.admin.command("ping")

    # ------CIERRE DE LA CONEXIÓN------
    async def close(self):
        """Cierra la conexión a MongoDB"""
        if self._client:
            self._client.close()
            self._db = None
            self._client = None

    # ------ELIMINACIÓN DE TODAS LAS COLECCIONES------
    async def drop_all_collections(self):
        """Elimina todas las colecciones de la base de datos"""
        collections = await self._db.list_collection_names()
        for collection in collections:
            await self._db[collection].drop()       

    # ------MANEJO DE COLECCIONES------
    def get_collection(self, collection_name: str):
        """Devuelve una colección específica"""
        if collection_name not in self._collections:
            raise ValueError(f"Collection {collection_name} is not defined.")
        return self._db[collection_name]