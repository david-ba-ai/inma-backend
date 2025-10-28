"""
Instancia global de configuración de variables de entorno y ajustes de la aplicación.
Utiliza Pydantic Settings para gestionar la configuración.
"""

from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict

# ------CONFIGURACIÓN DE POSTGRES------
class PostgresSettings(BaseSettings):
    model_config = ConfigDict(env_prefix="PG_", extra="ignore")

    user: str = Field(default="devuser")
    password: str = Field(default="devpassword")
    host: str = Field(default="postgres")
    port: int = Field(default=5432)
    db: str = Field(default="pg_db")
    ssl: bool = Field(default=False)

# ------CONFIGURACIÓN DE REDIS------
class RedisSettings(BaseSettings):
    model_config = ConfigDict(extra="ignore")

    host: str = Field(default="redis")
    port: int = Field(default=6379)
    password: str | None = None
    ssl: bool = Field(default=False)

# ------CONFIGURACIÓN DE MONGO------
class MongoSettings(BaseSettings):
    model_config = ConfigDict(extra="ignore")

    uri: str = Field(default="mongodb://mongo:27017")
    db_name: str = Field(default="mongo_db")

# ------CONFIGURACIÓN DE MODELOS DE LENGUAJE------
class IASettings(BaseSettings):
    model_config = ConfigDict(extra="ignore")

    openai_api_key: str | None = None
    langchain_api_key: str | None = None
    langchain_endpoint: str | None = None
    langchain_project: str | None = None

# ------CONFIGURACIÓN DE TWILIO------
class TwilioSettings(BaseSettings):
    model_config = ConfigDict(extra="ignore")

    account_sid: str | None = None
    auth_token: str | None = None
    to_number: str | None = None
    apikey_: str | None = None
    apikey_secret: str | None = None

# ------CONFIGURACIÓN GLOBAL------
class AppSettings(BaseSettings):
    model_config = ConfigDict(extra="ignore")

    # Variables generales
    env: str = "dev"
    debug: bool = False
    cors_allow_origins: str = ["*"]
    middleware_secret_key: str = None

    # Configuraciones específicas para bases de datos
    pg: PostgresSettings = PostgresSettings()
    mongo: MongoSettings = MongoSettings()
    redis: RedisSettings = RedisSettings()

    # Configuración específica para IA
    ia: IASettings = IASettings()

    # Configuración específica para Twilio
    twilio: TwilioSettings = TwilioSettings()

    # Otras variables de entonrno
    opencage_key: str | None = None


settings = AppSettings()