# 🐳 JobDevs - Guía de Docker

Guía completa para ejecutar el proyecto JobDevs usando Docker.

---

## Requisitos Previos

| Herramienta | Versión Mínima | Verificar |
|-------------|---------------|-----------|
| **Docker** | 20.10+ | `docker --version` |
| **Docker Compose** | 2.0+ | `docker compose version` |

> Si estás en Windows, instala [Docker Desktop](https://www.docker.com/products/docker-desktop/).

---

##  Inicio Rápido

### 1. Configurar variables de entorno

```bash
# El archivo .env.docker.example ya viene con valores por defecto para desarrollo
# Para producción, crea tu propio .env:
cp docker/.env.docker.example .env
# Edita .env y cambia las contraseñas
```

### 2. Construir y levantar todo

```bash
# Construir imágenes y levantar los 3 servicios
docker compose up --build -d
```

### 3. Verificar que todo esté corriendo

```bash
docker compose ps
```

Deberías ver 3 servicios `running` (o `healthy`):
- `teir_db` → PostgreSQL 16
- `teir_web` → Django + Gunicorn
- `teir_nginx` → Nginx

### 4. Acceder a la aplicación

Abre tu navegador en: **http://localhost**

---

##  Estructura de Archivos Docker

```
JobDevs/
├── Dockerfile              # Imagen multi-stage de Django
├── docker-compose.yml      # Orquestación de servicios
├── .dockerignore           # Archivos excluidos del build
├── docker/.env.docker.example # Variables de entorno (plantilla)
├── database/init.sql       # Schema DDL y triggers (se importa automáticamente)
└── docker/
    ├── entrypoint.sh       # Script de inicialización del contenedor web
    └── nginx/
        └── nginx.conf      # Configuración de Nginx
```

---

##  Comandos Útiles

### Gestión de Servicios

```bash
# Levantar todos los servicios
docker compose up -d

# Detener todos los servicios
docker compose down

# Detener y BORRAR volúmenes (⚠️ borra la base de datos)
docker compose down -v

# Reconstruir imágenes (después de cambios en el código)
docker compose up --build -d

# Ver estado de los servicios
docker compose ps
```

### Logs

```bash
# Ver logs de todos los servicios
docker compose logs

# Ver logs de un servicio específico (en tiempo real)
docker compose logs -f web
docker compose logs -f db
docker compose logs -f nginx

# Ver últimas 50 líneas
docker compose logs --tail=50 web
```

### Acceso a Contenedores

```bash
# Shell interactivo en el contenedor de Django
docker compose exec web bash

# Ejecutar comandos de Django
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py shell
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate

# Acceder a la consola de PostgreSQL
docker compose exec db psql -U teir_user -d teir_db
```

### Base de Datos

```bash
# Crear backup de la base de datos
docker compose exec db pg_dump -U teir_user teir_db > backup_$(date +%Y%m%d).sql

# Restaurar backup
docker compose exec -T db psql -U teir_user -d teir_db < backup.sql

# Reiniciar solo la base de datos
docker compose restart db
```

---

## Puertos

| Servicio | Puerto Host | Puerto Contenedor | Descripción |
|----------|------------|-------------------|-------------|
| Nginx | **80** | 80 | Punto de acceso principal |
| PostgreSQL | **5432** (local) | 5432 | Acceso local a BD (DBeaver, pgAdmin) |
| Gunicorn | — | 8000 | Solo accesible internamente |

> PostgreSQL está vinculado a `127.0.0.1:5432` en el host para evitar exposición externa no autorizada.

---

## Arquitectura

```
┌─────────────────────────────────────────────────────┐
│                   Docker Network                     │
│                                                      │
│  ┌──────────┐    ┌──────────────┐    ┌───────────┐  │
│  │  Nginx   │───▶│   Gunicorn   │───▶│PostgreSQL │  │
│  │  :80     │    │   (Django)   │    │  16       │  │
│  │          │    │   :8000      │    │  :5432    │  │
│  └──────────┘    └──────────────┘    └───────────┘  │
│       │                │                    │        │
│       ▼                ▼                    ▼        │
│  ┌─────────┐     ┌──────────┐       ┌───────────┐  │
│  │ static/ │     │  media/  │       │  postgres │  │
│  │ volume  │     │  volume  │       │   _data   │  │
│  └─────────┘     └──────────┘       └───────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## Solución de Problemas

### El contenedor web se reinicia continuamente

```bash
# Ver los logs para entender el error
docker compose logs web

# Causas comunes:
# - PostgreSQL no está listo todavía (espera unos segundos)
# - Credenciales incorrectas en el archivo .env
# - Error en migraciones de Django
```

### PostgreSQL no inicia

```bash
# Ver logs de PostgreSQL
docker compose logs db

# Si hay errores de permisos o datos corruptos:
docker compose down -v  # ⚠️ Esto borra la base de datos
docker compose up --build -d
```

### Migraciones y estructura de la base de datos

En PostgreSQL, la estructura y reglas de negocio son gestionadas directamente por el ORM y las migraciones de Django (se ejecutan automáticamente al iniciar mediante `docker/entrypoint.sh`). Si necesitás reaplicarlas manualmente:

```bash
docker compose exec web python manage.py migrate
```

### Puerto 80 ya está en uso

```bash
# Cambiar el puerto en docker-compose.yml
# Buscar la sección de nginx y cambiar "80:80" por "8080:80"
# Luego acceder en http://localhost:8080
```

### Los archivos estáticos no cargan (CSS/JS)

```bash
# Forzar recolección de estáticos
docker compose exec web python manage.py collectstatic --noinput

# Reiniciar nginx
docker compose restart nginx
```

---
