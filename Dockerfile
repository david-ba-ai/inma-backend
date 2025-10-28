# syntax=docker/dockerfile:1

########################################
# STAGE 1 — deps
# Instala dependencias desde pyproject.toml + uv.lock (reproducible)
########################################
FROM python:3.12-slim AS deps

# Variables de entorno básicas y limpieza
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Paquetes del sistema mínimos (solo lo necesario para compilar wheels si hace falta)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates build-essential pkg-config libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# Instalar UV
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
 && ln -s /root/.local/bin/uv /usr/local/bin/uv

# Copiamos los archivos de definición del proyecto
COPY pyproject.toml uv.lock ./

# Exportar dependencias del lockfile (sin incluir el proyecto raíz)
RUN uv export --frozen > /tmp/requirements.txt \
 && pip install --no-cache-dir --prefix=/install -r /tmp/requirements.txt


########################################
# STAGE 2 — build
# Instala tu proyecto dentro del entorno Python (NO editable)
########################################
FROM python:3.12-slim AS build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copiamos dependencias desde el stage anterior
COPY --from=deps /install /usr/local

# Copiamos TODO el repositorio (fuente + configs + prompts + resources)
COPY . .

# Instalamos el proyecto como paquete (no editable)
RUN pip install --no-cache-dir .


########################################
# STAGE 3 — runtime
# Imagen final: ligera, segura y rápida
########################################
FROM python:3.12-slim AS runtime

# Configuración base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Usuario no-root
RUN useradd -m appuser
USER appuser

# Copiar dependencias + proyecto ya instalado
COPY --from=build /usr/local /usr/local

# Copiar solo artefactos necesarios en tiempo de ejecución.
COPY prompts ./prompts
COPY config ./config
COPY resources ./resources

# Puerto expuesto (FastAPI/Uvicorn)
EXPOSE 8000

# Healthcheck para Docker/Kubernetes
HEALTHCHECK CMD curl -fs http://localhost:8000/health || exit 1

# Comando de inicio (multi-worker para producción)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]