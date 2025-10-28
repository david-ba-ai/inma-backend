import logging
import os
from twilio.rest import Client
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.background import BackgroundScheduler
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv

from src.core.settings import settings
from src.core.middleware import SessionMiddleware
from src.core.factories import create_mongo, create_redis, create_postgres
from src.services.sessions_service import SessionService
from src.services.messages_service import MessagesService
from src.services.user_service import UserService
from src.utils.logger_config import configure_logging
#from src.routers.base import main_router
from src.data_generation.load_app_data import load_app_data

# Configurar logging
configure_logging()
logger = logging.getLogger(__name__)

# ------ CICLO DE VIDA DE LA APLICACIÓN ------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la aplicación."""
    
    #------INSTANCIAS DE SERVICIOS Y BASE DE DATOS
    redis_cache = create_redis()  # Instancia de Redis        
    mongo_db = create_mongo()  # Instancia de MongoDB
    postgres_db = create_postgres()  # Instancia de PostgreSQL  
    
    #------INICIALIZAR Y PROBAR CONEXIONES
    try:
        await mongo_db.init_beanie() # Incializar Beanie
        await mongo_db.ping()
        logger.info("MongoDB connected successfully")

        await redis_cache.ping()
        logger.info("Redis connected successfully")

        await postgres_db.connect()
        await postgres_db.ping()
        logger.info("Postgres connected successfully")

    except Exception as e:
        logger.critical(f"Error initializing services: {e}")
        raise RuntimeError("Service initialization failed") from e
    
    #------REGISTRAR EN APP STATE
    app.state.mongodb = mongo_db
    app.state.redis_cache = redis_cache
    app.state.postgres = postgres_db
    app.state.messages_service = MessagesService(mongo_db) # Servicio de mensajes
    app.state.users_service = UserService(mongo_db) # Servicio de usuarios
    app.state.sessions_service = SessionService(redis_cache) # Servicio de sesiones
    
    #------CONFIGURAR TWILIO
    try:
        client = Client(settings.twilio.account_sid, settings.twilio.auth_token)
        app.state.twilio_client = client

    except Exception as e:
        pass

    #------CEDER CONTROL A LA APLICACIÓN
    yield
    
    #------CIERRE DE CONEXIONES
    try:
        await postgres_db.close()
        logger.info("Postgres connection closed.")
    except Exception as e:
        logger.error(f"Error closing Postgres: {e}")

    try:
        await mongo_db.close()
        logger.info("Mongo connection closed.")
    except Exception as e:
        logger.error(f"Error closing MongoDB: {e}")

    try:
        await redis_cache.close()
        logger.info("Redis connection closed.")
    except Exception as e:
        logger.error(f"Error closing Redis: {e}")
    

#------ARRANQUE DE LA APP------
def start_app() -> FastAPI:
    """Factory de la aplicación FastAPI"""    

    load_dotenv()
    
    #------INICIALIZAR LA APLICACIÓN
    app = FastAPI(
        title="Inma Backend API",
        description="API para el backend de Inma, la asistente virtual inmobiliaria.",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        lifespan=lifespan
    )

    #------MIDDLEWARE CORS
    try:
        allow_origins = settings.cors_allow_origins 

        app.add_middleware(
            CORSMiddleware,
            allow_origins=allow_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.info("CORS middleware running successfully...")
    except Exception as e:
        logger.critical(f"Error configuring CORS middleware: {e}")
        raise RuntimeError("Failed to configure CORS middleware") from e
    

    #------MIDDLEWARE DE SESIONES
    try:
        app.add_middleware(SessionMiddleware, secret_key=os.getenv("MIDDLEWARE_SECRET_KEY"))
        logger.info("Sessions middleware configured...")
    except Exception as e:
        logger.critical(f"Error initializing Sessions Middleware: {e}")
        raise
    

    #------ SCHEDULER PARA CARGA DE DATOS
    try:
        scheduler = BackgroundScheduler()
        scheduler.add_job(load_app_data, 'cron', hour=4, minute=0)
        scheduler.start()

    except Exception as e:
        logger.critical(f"Error configuring Cscheduler for update app data: {e}")
        raise RuntimeError(f"Error configuring Cscheduler for update app data: {e}")

    
    #------ARCHIVOS ESTÁTCOS
    try:
        static_dir = Path("static")
        static_dir.mkdir(exist_ok=True)
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
        logger.info("Static files mounted successfully...")
    except Exception as e:
        logger.critical(f"Error mounting static files: {e}")
        raise RuntimeError("Failed to mount static files") from e
    
    #------INCLUIR RUTAS
    """try:
        app.include_router(main_router())
        logger.info("Routes established successfully...")
    except Exception as e:
        logger.critical(f"Error including routers: {e}")
        raise RuntimeError("Failed to include routers") from e
    
    logger.info("App running succesfully.")"""
    
    return app

app = start_app()