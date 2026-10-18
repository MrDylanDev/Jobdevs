<p align="center">
  <img src="static/IMG/JobDevs.png" alt="JobDevs" width="800">
</p>

**Plataforma de vinculación entre empresas y talento SENA.**

[![CI](https://github.com/MrDylanDev/JobDevs/actions/workflows/ci.yml/badge.svg)](https://github.com/MrDylanDev/JobDevs/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-602%20passed-brightgreen)](https://github.com/MrDylanDev/JobDevs)
[![Python](https://img.shields.io/badge/python-3.14-blue)](https://python.org)
[![Django](https://img.shields.io/badge/django-5.0-092e20)](https://djangoproject.com)
[![PostgreSQL](https://img.shields.io/badge/postgresql-16-blue)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/docker-ready-2496ed)](https://docker.com)

---

## ¿Qué es JobDevs?

JobDevs conecta empresas con aprendices y egresados del SENA para desarrollar proyectos reales. Las empresas publican requerimientos, los desarrolladores se postulan, y la plataforma gestiona todo el ciclo: contratación, hitos, avances, revisión, finalización y calificación mutua.

|---

## Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                      USUARIOS                           │
│   Desarrollador           Empresa        Administrador  │
│   (postula, avanza)    (publica, revisa)  (gestiona)    │
└────────┬──────────────────────┬──────────────────┬──────┘
         │                      │                  │
         ▼                      ▼                  ▼
┌─────────────────────────────────────────────────────────┐
│                    DJANGO (MTV)                         │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │ usuarios │  │proyectos │  │ mensajes │  │  logs  │  │
│  ├──────────┤  ├──────────┤  ├──────────┤  ├────────┤  │
│  │avances   │  │postulac. │  │notificac.│  │favoritos│  │
│  ├──────────┤  ├──────────┤  └──────────┘  └────────┘  │
│  │contratac.│  │valoracion │                              │
│  └──────────┘  └──────────┘  9 apps modulares           │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│                  INFRAESTRUCTURA                         │
│                                                         │
│   Nginx :80  ──▶  Gunicorn :8000  ──▶  PostgreSQL :5432 │
│   (estáticos)     (3 workers)          (migraciones)    │
│                                                         │
│   Docker Compose  |  Health checks  |  Volúmenes        │
└─────────────────────────────────────────────────────────┘
```

**Flujo principal:**
```
Empresa publica proyecto → Dev se postula → Empresa acepta
→ Se crea contrato → Dev sube avances por hitos
→ Empresa revisa (acepta/rechaza) → Al completar todo
→ Empresa finaliza y califica → Dev califica a la empresa
```

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Backend | Django 5.0, Python 3.14 |
| Base de datos | PostgreSQL 16 (migraciones Django ORM) |
| Frontend | Django Templates, Bootstrap 5, Vanilla JS |
| Testing | pytest, pytest-django, Playwright |
| Contenedores | Docker, docker-compose, Gunicorn, Nginx |

---

## Funcionalidades principales

- **Registro dual** — Desarrollador (DEV) y Empresa (CORP) con perfiles independientes
- **Publicación de proyectos** — Empresas crean proyectos con vacantes, tipo de solución y prioridad
- **Postulación y contratación** — Desarrolladores aplican, empresas aceptan/rechazan
- **Sistema de hitos** — La empresa define entregables, asigna a equipos o al proyecto general
- **Avances con evidencias** — El desarrollador registra avances con URL de evidencia obligatoria
- **Flujo de revisión** — La empresa acepta o rechaza avances con comentario obligatorio
- **Chat por proyecto** — Espacio de trabajo grupal y chat privado 1-a-1
- **Calificación mutua** — Al finalizar, empresa califica al desarrollador y viceversa
- **Dashboard administrativo** — Panel maestro con búsqueda, filtros, acciones en lote, estadísticas y ranking de talento
- **API REST administrativa** — Endpoints para gestión de usuarios (CRUD, activación/suspensión en lote)
- **Recuperación de contraseña** — Token criptográfico por email con expiración de 1 hora
- **Auditoría completa** — Log de cambios de estado, triggers de integridad en MySQL, historial de estados

---

## Inicio rápido (Docker)

```bash
git clone https://github.com/MrDylanDev/JobDevs.git
cd JobDevs

# Configurar variables de entorno (obligatorio)
cp docker/.env.docker.example .env
# Editar .env con tus claves secretas

# Levantar los servicios con Docker Compose
docker compose up -d

# Para sembrar cuentas de prueba de desarrollo:
docker compose exec web python manage.py seed_demo_data
```

La aplicación estará disponible en `http://localhost`.

Para crear el primer administrador:

```bash
docker exec teir_web python manage.py createsuperuser
```

---

## Desarrollo local

### Requisitos

- Python 3.14+
- MySQL 8.0+

### Instalación

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configurar base de datos
cp docker/.env.docker.example .env
# Editar .env con tus credenciales de MySQL

python manage.py migrate
python manage.py runserver
```

### Variables de entorno

| Variable | Descripción | Default |
|----------|------------|---------|
| `DB_NAME` | Nombre de la base de datos | `tem_dbv2` |
| `DB_USER` | Usuario MySQL | `root` |
| `DB_PASSWORD` | Contraseña MySQL | — |
| `DB_HOST` | Host MySQL | `127.0.0.1` |
| `DJANGO_SECRET_KEY` | Clave secreta de Django | — |
| `DJANGO_DEBUG` | Modo debug | `False` |

---

## Tailwind CSS

El proyecto usa [django-tailwind](https://github.com/timonweb/django-tailwind) en modo **standalone** (binario de Tailwind CSS, sin Node.js) con la app `theme`.

```bash
# Compilar el CSS (obligatorio antes de collectstatic / deploy)
python manage.py tailwind build

# Desarrollo: watcher de Tailwind (en otra terminal, junto a runserver)
python manage.py tailwind start

# Desarrollo: Django + watcher de Tailwind juntos (requiere honcho)
python manage.py tailwind dev
```

- Fuente de estilos: `theme/static_src/src/styles.css` → compilado: `theme/static/css/dist/styles.css` (versionado).
- En plantillas: `{% load tailwind_tags %}` + `{% tailwind_css %}` (ya incluido en `templates/base.html`).
- Nunca editar el CSS compilado: se sobrescribe en cada `tailwind build`.

---

## Estructura del proyecto

```
JobDevs/
├── avances/           # Registro y revisión de avances
├── config/            # Configuración de Django (settings, urls, wsgi)
├── contrataciones/    # Gestión de contratos
├── database/          # Schema DDL y triggers MySQL
├── docker/            # Configuración de contenedores
│   ├── entrypoint.sh
│   ├── .env.docker.example
│   └── nginx/
├── docs/              # Documentación
│   ├── GUIA_USUARIO.md
│   ├── MANUAL_TECNICO.md
│   ├── API.md
│   └── DOCKER_README.md
├── favoritos/         # Proyectos guardados por el desarrollador
├── logs/              # Auditoría y reportes
├── mensajes/          # Chat y mensajería
├── notificaciones/    # Sistema de notificaciones
├── postulaciones/     # Postulaciones a proyectos
├── proyectos/         # Proyectos, hitos, equipos, valoraciones
├── static/            # CSS, JS, imágenes
├── templates/         # Templates Django por módulo
├── theme/             # App de Tailwind CSS (fuentes en static_src/, CSS compilado en static/css/dist/)
├── tests/             # Tests E2E con Playwright
├── usuarios/          # Autenticación, perfiles, dashboard admin
├── docker-compose.yml
├── Dockerfile
├── manage.py
├── requirements.txt
├── conftest.py        # Fixtures de pytest
├── pytest.ini         # Configuración de tests
├── .browserslistrc    # Política de compatibilidad de navegadores (RNF-12)
├── README.md
└── LICENSE
```

---

## Tests

```bash
# Tests de backend
pytest . --ignore=tests/e2e -v

# Tests E2E (requiere Playwright)
pytest tests/e2e/ -v -m e2e

# Tests E2E en un navegador concreto (chromium, chrome, firefox, edge)
E2E_BROWSERS=firefox pytest tests/e2e/ -v

# Todos los tests
pytest -v
```

**602 tests** (589 unit/integration + 13 E2E por navegador) cubriendo todas las apps: usuarios, proyectos, postulaciones, contrataciones, avances, mensajes, favoritos, logs, notificaciones y tests end-to-end con navegador real. En CI los E2E corren en Chrome, Firefox y Edge (ver [compatibilidad multi-navegador](docs/MANUAL_TECNICO.md#76-compatibilidad-multi-navegador-rnf-12)).

---

## Branch protection

Checks requeridos en `main`: `Test (SQLite)` (`test-sqlite`) y `Test (MySQL 8.0)` (`test-mysql`) deben estar en verde antes de merge. Configurar en GitHub → Settings → Branches → Branch protection rules → Require status checks to pass.

---

## Documentación

- [Guía de Usuario](docs/GUIA_USUARIO.md) — Manual para los 3 roles (Desarrollador, Empresa, Administrador)
- [Manual Técnico](docs/MANUAL_TECNICO.md) — Arquitectura, modelos, API, testing, despliegue
- [API Reference](docs/API.md) — Endpoints REST del panel de administración
- [Docker Guide](docs/DOCKER_README.md) — Configuración detallada de contenedores

## Licencia

MIT License. Ver [LICENSE](LICENSE) para el texto completo.
