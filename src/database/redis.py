"""
 Clase para manejar la conexión a Redis usando redis-py.
 En dev, usa host "redis" y puerto 6379 sin autenticación.
 """
from typing import Optional
from redis.asyncio import Redis
from contextlib import asynccontextmanager

class RedisCache:

    # ------INICIALIZACIÓN------
    def __init__(
        self,
        host: str = "redis",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        ssl: bool = False,
        decode_responses: bool = True,
    ) -> None:
        self._client: Optional[Redis] = Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            ssl=ssl,
            decode_responses=decode_responses,
        )

    # ------CONTEXTO ASÍNCRONO------
    @asynccontextmanager
    async def connection(self):
        """Permite usar RedisCache como contexto asíncrono."""
        try:
            yield self
        finally:
            await self.close()
    
    # ------VERIFICACIÓN DE LA CONEXIÓN------
    async def ping(self) -> bool:
        """Comprueba la conexión a Redis"""
        pong = await self._client.ping()
        return pong
    
    # ------VERIFICACIÓN DEL CLIENTE------
    async def _ensure_client(self) -> Redis:
        """Verifica que el cliente esté inicializado."""
        if self._client is None:
            raise RuntimeError("Redis client is not initialized or has been closed.")
        return self._client
    
    # ------CIERRE DE LA CONEXIÓN------
    async def close(self):
        """Cierra la conexión a Redis"""
        if self._client:
            self._client.close()
            self._client = None

    # ------ MÉTODOS CRUD ------
    async def get(self, key: str) -> Optional[str]:
        """Obtiene un valor de Redis"""
        client = await self._ensure_client()
        return await client.get(key)

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Almacena un valor en Redis con TTL opcional"""
        client = await self._ensure_client()
        if ttl and ttl > 0:
            return await client.setex(key, ttl, value)
        return await client.set(key, value)

    async def delete(self, key: str) -> int:
        """Elimina una clave de Redis"""
        client = await self._ensure_client()
        return await client.delete(key)

    async def exists(self, key: str) -> bool:
        """Verifica si una clave existe"""
        client = await self._ensure_client()
        return bool(await client.exists(key))

    async def expire(self, key: str, ttl: int) -> bool:
        """Establece un TTL para una clave existente"""
        client = await self._ensure_client()
        return bool(await client.expire(key, ttl))
    
    # ------BORRADO COMPLETO DE TODAS LAS BASES DE DATOS------
    async def flush_all(self):
        """Elimina todas las bases de datos de Redis."""
        client = await self._ensure_client()
        await client.flushall(asynchronous=True)