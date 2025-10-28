"""
Clase de gestión de conexión asíncrona a PostgreSQL.
Soporta entornos de desarrollo y producción mediante inyección de configuración.
"""

from __future__ import annotations
from typing import Any, Optional, List

import asyncpg
from contextlib import asynccontextmanager
from asyncpg import Pool, Record


class PostgresDatabase:
    """
    Gestor asíncrono de conexión a PostgreSQL.
    Soporta entornos de desarrollo y producción mediante inyección de configuración.
    """

    def __init__(
        self,
        user: str,
        password: str,
        host: str = "postgres",
        port: int = 5432,
        database: str = "postgres_db",
        ssl: bool = False,
        min_size: int = 1,
        max_size: int = 10,
    ) -> None:
        self._dsn = self._build_dsn(user, password, host, port, database, ssl)
        self._pool: Optional[Pool] = None
        self._min_size = min_size
        self._max_size = max_size

    # ------ CONEXIÓN ------
    async def connect(self) -> None:
        """Crea el pool de conexiones."""
        if not self._pool:
            self._pool = await asyncpg.create_pool(
                dsn=self._dsn,
                min_size=self._min_size,
                max_size=self._max_size,
            )

    # ------CIERRE DE LA CONEXIÓN------
    async def close(self) -> None:
        """Cierra el pool de conexiones."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    # ------CONTEXTO ASÍNCRONO------
    @asynccontextmanager
    async def connection(self):
        """Context manager que obtiene y libera una conexión del pool."""
        if not self._pool:
            raise RuntimeError("Database pool is not initialized. Call connect() first.")
        conn = await self._pool.acquire()
        try:
            yield conn
        finally:
            await self._pool.release(conn)

    # ------VERIFICACIÓN DE LA CONEXIÓN------
    async def ping(self) -> bool:
        """Verifica la conexión a PostgreSQL."""
        pool = await self._ensure_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1;")
            return result == 1

    # ------ MÉTODOS CRUD ------
    async def execute(self, query: str, *args) -> str:
        """Ejecuta una query de escritura (INSERT/UPDATE/DELETE)."""
        pool = await self._ensure_pool()
        async with pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch_one(self, query: str, *args) -> Optional[Record]:
        """Obtiene un único registro."""
        pool = await self._ensure_pool()
        async with pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetch_all(self, query: str, *args) -> List[Record]:
        """Obtiene múltiples registros."""
        pool = await self._ensure_pool()
        async with pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetch_val(self, query: str, *args) -> Any:
        """Obtiene un único valor (por ejemplo COUNT(*))"""
        pool = await self._ensure_pool()
        async with pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    # ------CREA EXTENSIONES------
    async def create_extension(self, name: str) -> None:
        """Activa extensiones si no existen (útil en dev)."""
        query = f"CREATE EXTENSION IF NOT EXISTS {name};"
        await self.execute(query)

    # ------CONSTRUCTOR DE DNS------
    @staticmethod
    def _build_dsn(user: str, password: str, host: str, port: int, database: str, ssl: bool) -> str:
        protocol = "postgresql"
        dsn = f"{protocol}://{user}:{password}@{host}:{port}/{database}"
        if ssl:
            dsn += "?sslmode=require"
        return dsn

    # ------VERIFICACIÓN DEL POOL------
    async def _ensure_pool(self) -> Pool:
        if not self._pool:
            raise RuntimeError("Connection pool not initialized. Call connect().")
        return self._pool