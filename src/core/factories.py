"""
Fábrica de instancias de bases de datos.
La configuración se define en src/config/db_settings.py.
Las funciones son llamadas desde el lifespan de la aplicación FastAPI.
"""

from src.core.settings import settings
from src.database.mongo import MongoDatabase
from src.database.redis import RedisCache
from src.database.postgres import PostgresDatabase


def create_mongo() -> MongoDatabase:
    return MongoDatabase(
        mongo_uri=settings.mongo.uri,
        mongo_db_name=settings.mongo.db_name
    )

def create_redis() -> RedisCache:
    return RedisCache(
        host=settings.redis.host,
        port=settings.redis.port,
        password=settings.redis.password,
        ssl=settings.redis.ssl,
    )


def create_postgres() -> PostgresDatabase:
    return PostgresDatabase(
        user=settings.pg.user,
        password=settings.pg.password,
        host=settings.pg.host,
        port=settings.pg.port,
        database=settings.pg.db,
        ssl=settings.pg.ssl,
    )