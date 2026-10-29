# Manual Técnico — JobDevs

> Documentación técnica para desarrolladores y operadores del sistema.
> Última actualización: 30 de junio de 2026.

---

## Índice

1. [Stack tecnológico](#1-stack-tecnológico)
2. [Arquitectura](#2-arquitectura)
3. [Modelo de datos](#3-modelo-de-datos)
4. [Instalación y desarrollo local](#4-instalación-y-desarrollo-local)
5. [Docker y despliegue](#5-docker-y-despliegue)
6. [API REST administrativa](#6-api-rest-administrativa)
7. [Sistema de testing](#7-sistema-de-testing)
8. [Triggers MySQL](#8-triggers-mysql)
9. [Vistas Django](#9-vistas-django)
10. [Seguridad](#10-seguridad)
11. [Variables de entorno](#11-variables-de-entorno)
12. [Estructura del proyecto](#12-estructura-del-proyecto)
13. [Flujos principales](#13-flujos-principales)

---

## 1. Stack tecnológico

| Capa | Tecnología | Versión |
|------|-----------|---------|
| Backend | Django | 6.1+ |
| Lenguaje | Python | 3.14+ |
| Base de datos | PostgreSQL (Producción) / SQLite (Tests) | 16+ |
| Driver PostgreSQL | psycopg2-binary | 2.9+ |
| Asincronismo / WebSockets | Django Channels + Daphne | 4.0+ |
| Broker / Cache | Redis | 7.0+ |
| Tareas en segundo plano | Celery + Celery Beat | 5.3+ |
| Correo en desarrollo | Mailpit | — |
| Servidor WSGI | Gunicorn | 22.0+ |
| Proxy reverso | Nginx | Alpine |
| Contenedores | Docker + Docker Compose | — |
| Frontend | Django Templates + Bootstrap 5 + Vanilla JS | — |
| Testing | pytest + pytest-django + pytest-cov | — |
| E2E | Playwright | — |

---

## 2. Arquitectura

### 2.1 Patrón general

JobDevs sigue una arquitectura **Django MTV (Model-Template-View)** desacoplada mediante una **capa de servicios de dominio (`services.py`) y políticas de autorización (`policies.py`)**, modularizada en 11 aplicaciones independientes:

```
config/          → settings, urls raíz, wsgi/asgi, celery
usuarios/        → auth, perfiles, dashboards, verificación SENA/empresas, API admin
proyectos/       → CRUD proyectos, hitos individuales/equipo, valoraciones, vitrina
postulaciones/   → postulación, negociación, rechazo formal, expiración de vacantes
contrataciones/  → Módulo 8: contrato digital, firmas electrónicas SHA-256, cancelaciones
avances/         → registro de entregables, revisión con idempotencia y guardas de estado
mensajes/        → chats directos y grupales, WebSockets asíncronos vía Channels y Redis
notificaciones/  → Server-Sent Events (SSE), alertas y depuración periódica con Celery Beat
favoritos/       → marcadores reactivos de proyectos favoritos
disputas/        → Módulo 10: arbitraje, sala de mediación a tres bandas y resolución
logs/            → auditoría de negocio (LogAuditoria), reportes CSV y visor técnico de logs
```

### 2.2 Patrones de diseño

- **Capa de Servicios y Políticas (`services.py` / `policies.py`)**: la lógica de negocio mutadora vive en servicios de dominio transaccionales, mientras las políticas de acceso aíslan los permisos del controlador.
- **Transacciones atómicas** (`transaction.atomic`) en operaciones críticas: formalizar contratación, resolver disputas, revisar avance, cancelar contrato.
- **Bloqueo pesimista** (`select_for_update`) para evitar race conditions en cupos de vacantes, concurrencia en avances y firmas digitales.
- **Inmutabilidad criptográfica**: cálculo determinista de hash SHA-256 (`hash_documento`) congelado en la primera firma de contratos digitales.
- **Mensajería asíncrona y SSE**: canales WebSockets backed por Redis para salas de chat y mediación, y Server-Sent Events para alertas de navbar.
- **Decoradores de seguridad**: `@login_required`, `@require_POST`, `@requiere_usuario_activo`, `@api_ratelimit`.

### 2.3 Diagrama de despliegue

```
[Cliente / Navegador]
       │
   (Puerto 80)
       ▼
    [Nginx]
   ┌───┴──────────────────────────────┐
   │ HTTP (:8000)                     │ WS (:8001 /ws/)
   ▼                                  ▼
[Gunicorn]                         [Daphne]
   │                                  │
   └───► [Django Core / ASGI / Celery] ◄───┘
             │              │
      (PostgreSQL 16)    (Redis 7)
             │              │
        [Database]     [Channels & Tasks]
```

---

## 3. Modelo de datos

### 3.1 Usuario (`usuarios`)

```python
Usuario(AbstractUser):
    first_name = None           # desactivado
    last_name = None            # desactivado
    nombre: CharField(150)
    identificacion: CharField(20, unique, nullable)
    fecha_nacimiento: DateField(nullable)
    email: EmailField(150, unique)
    rol: CharField(choices=[empresa, desarrollador, administrador])
    estado: CharField(choices=[activo, inactivo, suspendido])
    token_recuperacion: CharField(255, nullable)  # token criptográfico
    token_expiracion: DateTimeField(nullable)
    intentos_fallidos: PositiveSmallIntegerField(default=0)

PerfilEmpresa:
    usuario: OneToOneField(Usuario)
    nombre_empresa, sector, telefono, ciudad, descripcion
    logo: ImageField
    calificacion_promedio: DecimalField

PerfilDesarrollador:
    usuario: OneToOneField(Usuario)
    programa_formacion, ficha, habilidades
    foto_perfil: ImageField
    portafolio_url: URLField
    calificacion_promedio: DecimalField
    num_proyectos_completados: IntegerField
```

### 3.2 Proyecto (`proyectos`)

```python
Proyecto:
    empresa: FK(Usuario)
    titulo, descripcion, tipo_solucion(choices), prioridad(choices)
    vacantes: PositiveIntegerField
    estado: CharField(choices=[
        publicado, en_desarrollo,
        en_revision, finalizado, rechazado, inactivo
    ])
    fecha_publicacion: auto_now_add
    fecha_limite: DateField(nullable)

Entregable (Hito):
    proyecto: FK(Proyecto)
    equipo: FK(Equipo, nullable)
    titulo, descripcion
    estado: CharField(choices=[pendiente, en_revision, completado])

Equipo:
    nombre, proyecto: FK(Proyecto)
    miembros: M2M(Usuario)

Valoracion:
    proyecto, empresa, desarrollador: FK
    rol_evaluador: CharField(choices=[empresa, desarrollador])
    puntuacion: PositiveSmallIntegerField(1-5)
    comentario: TextField(nullable)

HistorialEstadoProyecto:
    proyecto: FK(Proyecto)
    estado_anterior, estado_nuevo: CharField
    cambiado_por: FK(Usuario, SET_NULL)
    fecha: auto_now_add
```

### 3.3 Postulación y Contratación

```python
Postulacion:
    proyecto: FK(Proyecto), desarrollador: FK(Usuario)
    mensaje: TextField(nullable)
    estado: CharField(choices=[pendiente, aceptada, rechazada])
    unique_together: (proyecto, desarrollador)

Contratacion:
    proyecto: FK(Proyecto), desarrollador: FK(Usuario), empresa: FK(Usuario)
    fecha_inicio: DateField(auto_now_add)
    estado: CharField(choices=[activa, finalizada, cancelada])
    unique_together: (proyecto, desarrollador)
```

### 3.4 Avance

```python
Avance:
    proyecto: FK(Proyecto), desarrollador: FK(Usuario)
    entregable: FK(Entregable)
    descripcion: TextField
    archivo_url: CharField(500)  # obligatorio
    estado: CharField(choices=[pendiente, aceptado, rechazado])
    comentario_revision: TextField(nullable)
```

### 3.5 Mensajería y Notificaciones

```python
Mensaje:
    remitente, receptor: FK(Usuario) (receptor nullable = grupal)
    proyecto: FK(Proyecto, SET_NULL)
    titulo, contenido, leido: BooleanField

Notificacion:
    usuario, proyecto: FK
    tipo: CharField(choices)
    mensaje: TextField, leida: BooleanField
```

### 3.6 Auditoría

```python
LogAuditoria:
    usuario: FK(Usuario, SET_NULL)
    accion: CharField(300)
    tabla_afectada: CharField(nullable)
    registro_id: BigIntegerField(nullable)

CopiaSeguridad:
    ejecutado_por: FK(Usuario, SET_NULL)
    archivo_url, tamano_mb, estado(choices)
```

---

## 4. Instalación y desarrollo local

### 4.1 Requisitos

- Python 3.14+
- MySQL 8.0+
- pip

### 4.2 Setup

```bash
git clone https://github.com/MrDylanDev/JobDevs.git
cd JobDevs
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configurar base de datos
cp docker/.env.docker.example .env
# Editar .env con credenciales reales de MySQL:
#   DB_NAME=tem_dbv2
#   DB_USER=root
#   DB_PASSWORD=tu_password
#   DB_HOST=127.0.0.1
#   DJANGO_SECRET_KEY=generar_una_key_segura
#   DJANGO_DEBUG=True

# Inicializar BD
python manage.py migrate
python manage.py runserver
```

### 4.3 Crear superusuario

```bash
python manage.py createsuperuser
# Rol: administrador
```

### 4.4 Cargar schema MySQL (triggers)

El archivo `database/init.sql` contiene el DDL completo con triggers. Para desarrollo local, ejecutar solo los triggers:

```bash
mysql -u root -p tem_dbv2 < database/init.sql
```

El sistema verificará la existencia de triggers al iniciar mediante `usuarios/checks.py`.

---

## 5. Docker y despliegue
### 5.1 Requisitos
- Docker


### 5.2 Servicios

```yaml
services:
  db:      # PostgreSQL 16, puerto 5432 (interno)
  web:     # Django + Gunicorn, puerto 8000 (interno)
  nginx:   # Nginx Alpine, puerto 80
  backup:  # Respaldo diario de la base de datos (RNF-14), sin puertos publicados
```

### 5.3 Inicio rápido

```bash
cp docker/.env.docker.example .env
# Editar .env con secretos reales
docker compose up -d
```

La aplicación en `http://localhost`.

### 5.4 Entrypoint

`docker/entrypoint.sh` ejecuta en orden:
1. Espera conexión MySQL (30 reintentos, 2s cada uno)
2. `python manage.py migrate --noinput`
3. `python manage.py collectstatic --noinput`
4. `gunicorn config.wsgi:application` con 3 workers, 2 threads c/u

### 5.5 Gunicorn

```bash
gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --worker-class gthread \
    --threads 2 \
    --timeout 120 \
    --max-requests 1000 \
    --max-requests-jitter 50
```

### 5.6 Nginx

- Sirve `/static/` con cache 30 días
- Sirve `/media/` con cache 7 días
- Proxy reverso a Gunicorn en `web:8000`
- Health check en `/health/`
- Headers de seguridad: `X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection`
- Gzip compresión nivel 6
- Bloqueo de archivos ocultos (`.env`, `.git`)

### 5.7 Health checks

```bash
# MySQL
docker exec teir_db mysqladmin ping -h localhost

# Web
docker exec teir_web curl -f http://localhost:8000/

# Nginx
curl -f http://localhost/health/
```

---

## 6. API REST administrativa

### 6.1 Autenticación

Todas las rutas requieren:
- Sesión activa con rol `administrador`
- Token CSRF en header `X-CSRFToken`

### 6.2 Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/` | Listar todos los usuarios |
| GET | `/api/<id>/` | Obtener usuario por ID |
| POST | `/api/crear/` | Crear usuario |
| PUT | `/api/<id>/actualizar/` | Actualizar usuario |
| DELETE | `/api/<id>/eliminar/` | Eliminar usuario |
| POST | `/api/bulk-toggle/` | Activar/suspender en lote |

### 6.3 Crear usuario

```json
POST /api/crear/
{
  "username": "nuevo_dev",
  "email": "dev@jobdevs.edu.co",
  "password": "SecurePass123!",
  "rol": "desarrollador"
}
```

Respuesta `201`:
```json
{"id": 5, "status": "created"}
```

### 6.4 Bulk toggle

```json
POST /api/bulk-toggle/
{
  "ids": [1, 2, 3],
  "action": "suspend"  // o "activate"
}
```

Validaciones:
- No se puede suspender al admin que ejecuta la acción
- `activate`: `estado='activo'`, `is_active=True`
- `suspend`: `estado='suspendido'`, `is_active=False`

### 6.5 Códigos de error

| Código | Significado |
|--------|------------|
| 200 | Éxito |
| 201 | Creado |
| 400 | Datos inválidos |
| 403 | No es administrador |
| 404 | No encontrado |
| 405 | Método no permitido |
| 409 | Conflicto (username/email duplicado) |
| 500 | Error interno |

---

## 7. Sistema de testing

### 7.1 Configuración

```ini
# pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings_test
python_files = tests.py test_*.py *_tests.py
addopts = -v --tb=short --strict-markers -p no:warnings
markers =
    slow: tests lentos
    e2e: tests end-to-end con Playwright
```

### 7.2 Settings de test

`config/settings_test.py`:
- SQLite en memoria (`:memory:`)
- Validadores de password desactivados
- MD5 hasher (rápido)
- Email backend: `locmem`
- Monkey-patch para rename de columna `cedula` → `identificacion`

### 7.3 Fixtures globales (`conftest.py`)

```python
client()              # Django test client sin auth
admin_user(db)        # Usuario admin activo
empresa_user(db)      # Usuario empresa activo
desarrollador_user(db) # Usuario desarrollador activo
suspended_user(db)    # Usuario suspendido
auth_client()         # Client autenticado como empresa
admin_client()        # Client autenticado como admin
dev_client()          # Client autenticado como desarrollador
```

### 7.4 Ejecutar tests

```bash
# Unitarios e integración (sin E2E)
pytest . --ignore=tests/e2e -v

# Solo E2E (requiere Playwright y navegador)
pytest tests/e2e/ -v -m e2e

# E2E en un navegador concreto (ver sección 7.6)
E2E_BROWSERS=firefox pytest tests/e2e/ -v

# Todos
pytest -v
```

### 7.5 Cobertura

```
apps con tests:
  usuarios/       → test_admin.py, test_auth.py, test_dashboard.py, test_registro.py
  proyectos/      → test_models.py, test_views.py
  postulaciones/  → test_postulaciones.py
  contrataciones/ → test_contrataciones.py
  avances/        → test_avances.py
  mensajes/       → test_mensajes.py
  favoritos/      → test_favoritos.py
  logs/           → test_logs.py
  notificaciones/ → test_notificaciones.py
  tests/e2e/      → test_full_workflow.py, test_auth_flows.py, test_avance_workflow.py

Total: 602 tests recolectados (589 unitarios/integración + 13 E2E por navegador)
```

---

### 7.6 Compatibilidad multi-navegador (RNF-12)

La plataforma se usa desde las **últimas versiones estables de Chrome, Firefox y Edge**.
No se da soporte a navegadores con más de dos versiones de antigüedad, a Internet
Explorer ni a navegadores móviles (el diseño es responsive, pero no se verifica con E2E).

### Navegadores soportados

| Navegador | Soporte | Verificación automática en CI |
|---|---|---|
| Google Chrome | Últimas 2 versiones estables | Job `E2E (chrome)` — canal `chrome` del runner |
| Microsoft Edge | Últimas 2 versiones estables | Job `E2E (edge)` — canal `msedge` del runner |
| Mozilla Firefox | Últimas 2 versiones estables | Job `E2E (firefox)` — Firefox instalado por Playwright |
| Chromium | Soportado (motor de Chrome y Edge) | Local / opcional: `E2E_BROWSERS=chromium` |
| Safari (WebKit) | Fuera de alcance | — |

El workflow `.github/workflows/ci.yml` (job `test-e2e`) ejecuta los 13 tests E2E en una
matriz de 3 navegadores, con `fail-fast: false` para que un fallo en un navegador no
oculte el resultado de los demás. Chrome y Edge se toman de los binarios que ya traen
los runners de GitHub (`channel='chrome'` / `channel='msedge'`); Firefox lo instala
Playwright (`playwright install --with-deps firefox`).

### Ejecutar los E2E en local

La variable de entorno `E2E_BROWSERS` selecciona el navegador (por defecto `chromium`):

```bash
# Navegador por defecto (Chromium de Playwright)
pytest tests/e2e -v

# Un navegador concreto
E2E_BROWSERS=firefox pytest tests/e2e -v

# Varios navegadores en una misma sesión
E2E_BROWSERS=chrome,firefox,edge pytest tests/e2e -v
```

Valores admitidos: `chromium`, `chrome`, `firefox`, `edge`. Los canales `chrome` y
`edge` usan los navegadores instalados en el sistema; los motores propios de Playwright
se instalan una vez con:

```bash
playwright install --with-deps chromium firefox
```

Al iniciar cada sesión se registra la versión realmente usada, lo que sirve como
evidencia de la verificación:

```
[E2E] navegador firefox: versión 157.0
```

### Restricciones de compatibilidad

- **JavaScript**: no hay SPA ni jQuery. El único JS externo es el bundle de Bootstrap;
  el resto es JS propio sin transpilar, que no depende de APIs experimentales.
- **Dependencias por CDN**: Bootstrap 5.3.3 y Font Awesome 6.5.0 (ambos con soporte
  amplio) y Google Fonts. Si un CDN falla, la página sigue siendo usable; sólo se pierde
  el estilo.
- **Scrollbars**: los estilos propios usan `::-webkit-scrollbar`. Cada bloque incluye su
  equivalente estándar (`scrollbar-width` / `scrollbar-color`) dentro de
  `@supports not selector(::-webkit-scrollbar)`: Chromium conserva su estilo actual y
  Firefox obtiene la scrollbar equivalente.
- **CSS moderno**: si se incorpora una herramienta que emita sintaxis como `@property`,
  `color-mix()`, `oklch()` o `@layer` (por ejemplo, las utilidades de Tailwind CSS v4),
  el mínimo técnico sube a **Chrome/Edge 111+, Firefox 128+ y Safari 16.4+**. En ese caso
  hay que actualizar esta matriz.
- La política se declara también en `.browserslistrc` (referencia para futuras
  herramientas de build; hoy no hay pipeline de Node).

---

## 8. Triggers MySQL

### 8.1 Lista de triggers requeridos

Verificados al iniciar Django por `usuarios/checks.py`:

| Trigger | Función |
|---------|---------|
| `trg_validar_vacantes_antes_de_contratar` | Evita exceder vacantes al contratar |
| `trg_notificacion_mensaje` | Crea notificación al enviar mensaje |
| `trg_nueva_postulacion` | Notifica a la empresa cuando alguien se postula |
| `trg_actualizar_proyectos_completados` | Actualiza contador de proyectos del dev |
| `trg_log_nuevo_usuario` | Registra creación de usuarios en LogAuditoria |
| `trg_registro_sesion` | Registra inicio de sesión |
| `trg_log_usuario_modificado` | Registra modificación de usuarios |

### 8.2 Verificación

```bash
mysql -u root -p -e "SHOW TRIGGERS" tem_dbv2
```

Si falta algún trigger, Django emite un Warning al iniciar. Ejecutar `database/init.sql` para restaurarlos.

---

## 9. Vistas Django

### 9.1 Estructura de vistas

El paquete `usuarios/views/` está modularizado:

```
usuarios/views/
├── __init__.py              # re-exporta todas las vistas
├── _helpers.py              # get_notificaciones_context()
├── auth_views.py            # login, logout, recuperar, restablecer
├── registration_views.py    # registro
├── dashboard_views.py       # inicio (landing page)
├── profile_views.py         # editar_perfil
├── empresa_dashboard.py     # dashboard_empresa
├── dev_dashboard.py         # dashboard_desarrollador
├── admin_dashboard.py       # dashboard_admin + admin_toggle + admin_reactivar
└── admin_api.py             # api_usuarios + CRUD + bulk_toggle
```

### 9.2 Decoradores de acceso

```python
@login_required              # requiere sesión activa
@require_POST                # solo acepta POST
@requiere_usuario_activo     # bloquea usuarios suspendidos/inactivos
```

### 9.3 URLs principales

```
/                           → landing page (inicio)
/login/                     → login
/logout/                    → logout
/registro/                  → registro
/recuperar/                 → recuperar contraseña
/restablecer/<token>/       → restablecer contraseña

/empresa/dashboard/         → dashboard empresa
/desarrollador/dashboard/   → dashboard desarrollador
/admin/dashboard/           → dashboard administrador
/perfil/editar/             → editar perfil

/proyectos/listar/          → listar proyectos
/proyectos/crear/           → publicar proyecto
/proyectos/<id>/finalizar/  → finalizar proyecto
/proyectos/<id>/calificar/  → calificar empresa (dev)
/proyectos/<id>/hitos/      → gestionar hitos
/proyectos/<id>/equipos/    → gestionar equipos

/postulaciones/<id>/        → ver postulaciones (empresa)
/postulaciones/postularse/<id>/ → postularse (dev)
/postulaciones/aceptar/<id>/    → aceptar postulación

/contrataciones/            → lista contrataciones (empresa)
/contrataciones/<id>/cancelar/  → cancelar contrato

/avances/<proyecto_id>/     → registrar avance (dev)
/avances/revisar/<id>/      → revisar avance (empresa)
/avances/ver/<proyecto_id>/ → ver avances

/mensajes/sala/<proyecto_id>/     → chat grupal
/mensajes/chat/<receptor_id>/<proyecto_id>/ → chat privado
/mensajes/inbox/                  → bandeja de entrada
/mensajes/sent/                   → enviados
/mensajes/redactar/               → redactar mensaje

/notificaciones/                  → lista notificaciones
/notificaciones/marcar-leidas/    → marcar leídas

/favoritos/toggle/<proyecto_id>/  → toggle favorito
/favoritos/                       → listar favoritos

/logs/reporte/                    → reporte de logs

/api/                             → API REST (admin only)
/api/crear/                       → crear usuario
/api/bulk-toggle/                 → acciones en lote
```

---

## 10. Seguridad

### 10.1 Contraseñas

- Validación custom: 8+ caracteres, mayúscula, minúscula, número
- Hashing: PBKDF2 (principal), Argon2 y BCrypt (fallback)
- Recuperación: token `secrets.token_urlsafe(32)`, expira en 1 hora
- Sin fuga de información: mismo mensaje para email existente y no existente

### 10.2 Sesiones

- `SESSION_COOKIE_AGE = 3600` (1 hora)
- `SESSION_EXPIRE_AT_BROWSER_CLOSE = True`
- `SESSION_SAVE_EVERY_REQUEST = True`
- Bloqueo por fuerza bruta: 5 intentos fallidos → cuenta suspendida

### 10.3 CSRF

- `CSRF_TRUSTED_ORIGINS` configurado para localhost
- Token CSRF requerido en API

### 10.4 Docker

- Usuario no-root (`appuser`)
- `.env` en `.gitignore`
- Health checks en los 3 servicios
- Sin puertos expuestos excepto 80 (Nginx) y 3307 (MySQL dev)

### 10.5 Consideraciones

- `SECRET_KEY` obligatoria en producción (levanta `ValueError` si falta)
- Sin rate limiting en API admin (issue SCRUM-141)
- `ALLOWED_HOSTS` sin `.strip()` — usar sin espacios (issue SCRUM-137)
- Contraseñas con defaults en `docker-compose.yml` (issue SCRUM-147)

---

## 11. Variables de entorno

| Variable | Descripción | Default |
|----------|------------|---------|
| `DJANGO_SECRET_KEY` | Clave secreta Django | Obligatorio en prod |
| `DJANGO_DEBUG` | Modo debug | `False` |
| `DJANGO_ALLOWED_HOSTS` | Hosts permitidos (separados por coma) | `localhost,127.0.0.1` |
| `DB_NAME` | Nombre BD PostgreSQL | `jobdevs_db` |
| `DB_USER` | Usuario PostgreSQL | `postgres` |
| `DB_PASSWORD` | Contraseña PostgreSQL | — |
| `DB_HOST` | Host PostgreSQL | `127.0.0.1` |
| `DB_PORT` | Puerto PostgreSQL | `5432` |
| `REDIS_URL` | URL de broker Redis para Channels y Celery | `redis://127.0.0.1:6379/0` |
| `CELERY_BROKER_URL` | Broker para tareas asíncronas | `redis://127.0.0.1:6379/0` |
| `EMAIL_BACKEND` | Backend de email | `console.EmailBackend` |
| `EMAIL_HOST` | Servidor SMTP (Mailpit en dev) | `localhost` |
| `EMAIL_PORT` | Puerto SMTP (1025 en Mailpit) | `1025` |
| `DEFAULT_FROM_EMAIL` | Remitente default | `JobDevs <noreply@jobdevs.edu.co>` |
| `CLOUDFLARE_R2_ACCOUNT_ID` | Account ID de Cloudflare | Vacío (modo local) |
| `CLOUDFLARE_R2_ACCESS_KEY_ID` | Access Key ID de token R2 | Vacío (modo local) |
| `CLOUDFLARE_R2_SECRET_ACCESS_KEY` | Secret Access Key de token R2 | Vacío (modo local) |
| `CLOUDFLARE_R2_BUCKET_NAME` | Nombre del bucket R2 privado | Vacío (modo local) |
| `CLOUDFLARE_R2_ENDPOINT_URL` | Endpoint S3 de R2 | `https://{ACCOUNT_ID}.r2.cloudflarestorage.com` |
| `R2_UPLOAD_URL_EXPIRACION_SEGUNDOS` | Tiempo de vida para URL PUT de subida directa | `300` (5 minutos) |
| `R2_DOWNLOAD_URL_EXPIRACION_SEGUNDOS` | Tiempo de vida para URL GET de descarga protegida | `900` (15 minutos) |

---

## 12. Estructura del proyecto

```
JobDevs/
├── avances/              # App: registro y revisión de avances
│   ├── models.py         #   Avance
│   ├── views.py          #   registrar_avance, revisar_avance, ver_avances
│   ├── urls.py
│   └── tests/
├── config/               # Configuración Django
│   ├── settings.py       #   Producción (MySQL)
│   ├── settings_test.py  #   Testing (SQLite en memoria)
│   ├── urls.py           #   URLconf raíz
│   ├── wsgi.py
│   └── asgi.py
├── contrataciones/       # App: gestión de contratos
│   ├── models.py         #   Contratacion
│   └── views.py          #   listar, detalle, cancelar
├── database/
│   └── init.sql          # Schema DDL + triggers MySQL
├── docker/
│   ├── entrypoint.sh     # Script de inicio del contenedor
│   ├── .env.docker.example
│   └── nginx/nginx.conf  # Configuración Nginx
├── docs/
│   └── API.md            # Documentación de API REST
├── favoritos/            # App: proyectos guardados
│   ├── models.py         #   Favorito
│   └── views.py          #   toggle_favorito, listar_favoritos
├── logs/                 # App: auditoría
│   ├── models.py         #   LogAuditoria, CopiaSeguridad
│   └── views.py
├── mensajes/             # App: chat y mensajería
│   ├── models.py         #   Mensaje
│   └── views.py          #   sala_chat, sala_chat_grupal, inbox, sent, redactar
├── notificaciones/       # App: sistema de alertas
│   ├── models.py         #   Notificacion
│   └── views.py
├── postulaciones/        # App: postulaciones
│   ├── models.py         #   Postulacion
│   └── views.py          #   ver_postulaciones, postularse, aceptar
├── proyectos/            # App: core del negocio
│   ├── models.py         #   Proyecto, Entregable, Equipo, Valoracion, HistorialEstado
│   └── views.py          #   listar, crear, finalizar, calificar, hitos, equipos
├── static/               # CSS, JS, imágenes
│   ├── publico/          #   Landing page
│   ├── dashboard/        #   Dashboards
│   ├── Desarrollador/    #   Perfil desarrollador
│   ├── empresa/          #   Panel empresa
│   └── administrador/    #   Panel admin
├── templates/            # Django templates
├── tests/
│   └── e2e/              # Tests end-to-end con Playwright
├── usuarios/             # App: auth y perfiles
│   ├── models.py         #   Usuario, PerfilEmpresa, PerfilDesarrollador
│   ├── forms.py          #   RegistroUsuarioForm, PerfilEmpresaForm, PerfilDesarrolladorForm
│   ├── validators.py     #   ComplexPasswordValidator
│   ├── decorators.py     #   requiere_usuario_activo
│   ├── checks.py         #   Verificación de triggers MySQL
│   ├── utils.py          #   get_admin_id, get_admin_ids (con caché)
│   └── views/            #   Paquete modular de vistas
├── conftest.py           # Fixtures globales de pytest
├── pytest.ini            # Configuración de pytest
├── manage.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 13. Flujos principales

### 13.1 Ciclo de vida del proyecto

```
publicado → (primera contratación) → en_desarrollo
                                     ↓
                          (todos los hitos enviados)
                                     ↓
                                en_revision
                                     ↓
                          (empresa acepta todos, califica)
                                     ↓
                                finalizado
```

**Estados intermedios:**
- `rechazado`: proyecto rechazado por admin (no usado actualmente)
- `inactivo`: proyecto desactivado por la empresa

**Cambios de estado por eventos:**
- Aceptar postulación: `publicado` → `en_desarrollo`
- Rechazar un avance: `en_revision` → `en_desarrollo`
- Último hito enviado: `en_desarrollo` → `en_revision`
- Finalizar proyecto: `en_revision` → `finalizado`
- Desactivar proyecto: `publicado` o `en_desarrollo` → `inactivo`

### 13.2 Flujo de postulación

```
1. Empresa publica proyecto (estado: publicado)
2. Desarrollador se postula (estado postulación: pendiente)
3. Empresa acepta postulación
   ├── Crea Contratacion (estado: activa)
   ├── Cambia estado proyecto → en_desarrollo
   ├── Agrega dev al equipo del proyecto
   └── Registra en LogAuditoria
4. Desarrollador trabaja en hitos
5. Empresa revisa avances
6. Empresa finaliza y califica
7. Desarrollador califica a la empresa
```

### 13.3 Flujo de hitos y avances

```
1. Empresa crea Entregable (estado: pendiente)
   ├── Asignado a equipo → notifica miembros del equipo
   └── Sin equipo → notifica todos los contratados
2. Desarrollador registra Avance
   ├── archivo_url obligatorio
   ├── Cambia estado hito → en_revision
   └── Notifica a la empresa
3. Empresa revisa avance:
   ├── Aceptar:
   │   ├── Cambia estado hito → completado
   │   └── Notifica al desarrollador
   └── Rechazar:
       ├── Requiere comentario obligatorio
       ├── Cambia estado hito → pendiente
       ├── Cambia estado proyecto → en_desarrollo
       └── Notifica al desarrollador
4. Si es el último hito → proyecto → en_revision
```

### 13.4 Transacciones atómicas

Las siguientes operaciones usan `transaction.atomic()` + `select_for_update()`:

| Operación | Archivo | Bloqueo sobre |
|-----------|---------|---------------|
| Finalizar proyecto | `proyectos/views.py` | `Proyecto` |
| Aceptar postulación | `postulaciones/views.py` | `Postulacion` |
| Cancelar contrato | `contrataciones/views.py` | `Contratacion` |
| Registrar avance | `avances/views.py` | `Proyecto` |
| Revisar avance | `avances/views.py` | (implícito por `Avance`) |
| Desactivar proyecto | `proyectos/views.py` | (implícito por `Proyecto`) |

### 13.5 Sincronización de caché admin

Cuando se crea, modifica o elimina un administrador:
```python
cache.delete('admin_id')
cache.delete('admin_ids_list')
```

---

## 14. Base de datos

### 14.1 Motor y configuración

| Parámetro | Desarrollo | Testing | Producción (Docker) |
|-----------|-----------|---------|---------------------|
| Motor | MySQL 8.0 | SQLite :memory: | MySQL 8.0 |
| Driver | PyMySQL | sqlite3 | PyMySQL |
| Host | 127.0.0.1 | — | db (nombre del servicio) |
| Puerto | 3306 | — | 3306 |
| charset | utf8mb4 | — | utf8mb4 |

### 14.2 Índices definidos

| Tabla | Índice | Columnas |
|-------|--------|----------|
| proyectos | idx_estado | estado |
| proyectos | idx_proy_tipo | tipo_solucion |
| proyectos | idx_proy_prio | prioridad |
| proyectos | idx_fecha_publicacion | fecha_publicacion |
| contrataciones | idx_proy_dev_est | proyecto, desarrollador, estado |
| contrataciones | idx_empresa_contratos | empresa |
| entregables | idx_entregables_estado | estado |
| entregables | idx_entregables_fecha | fecha_creacion |

### 14.3 Constraints UNIQUE

| Tabla | Columnas |
|-------|----------|
| postulaciones | (proyecto_id, desarrollador_id) |
| contrataciones | (proyecto_id, desarrollador_id) |
| favoritos | (desarrollador_id, proyecto_id) |
| valoraciones | (proyecto_id, desarrollador_id, rol_evaluador) |

### 14.4 Migraciones

```bash
# Generar migraciones después de cambiar modelos
python manage.py makemigrations

# Aplicar migraciones pendientes
python manage.py migrate

# Ver estado de migraciones
python manage.py showmigrations

# Revertir última migración (development only)
python manage.py migrate <app_name> <numero_anterior>
```

**Nota:** El proyecto usa `settings_test.py` con SQLite en memoria para tests. La migración 0005 de usuarios usa `SeparateDatabaseAndState` porque la columna `cedula` se renombró manualmente en MySQL. El `conftest.py` aplica un monkey-patch para que SQLite maneje este caso correctamente.

### 14.5 Relación modelos Django ↔ tablas PostgreSQL

| Modelo Django | Tabla BD | Aplicación | Descripción |
|---------------|----------|------------|-------------|
| Usuario | usuarios | usuarios | Custom User con roles y estados |
| PerfilEmpresa | perfil_empresa | usuarios | Perfil corporativo y estado de verificación |
| PerfilDesarrollador | perfil_desarrollador | usuarios | Perfil dev, condición SENA y reputación |
| FichaSena | fichas_sena | usuarios | Padrón oficial institucional SENA (Lista Blanca) |
| ExcepcionFichaSena | excepciones_ficha_sena | usuarios | Excepciones autorizadas a la lista blanca |
| Proyecto | proyectos | proyectos | Proyectos con prioridades y ciclo de vida |
| Entregable | entregables | proyectos | Hitos individuales o de equipo |
| Equipo | equipos | proyectos | Equipos de colaboradores |
| Postulacion | postulaciones | postulaciones | Postulaciones y negociación precontractual |
| Contratacion | contrataciones | contrataciones | Contrataciones activas, cupos y cancelaciones |
| ContratoDigital | contratos_digitales | contrataciones | Módulo 8: Contrato digital y firmas SHA-256 |
| Valoracion | valoraciones | proyectos | Calificaciones bidireccionales por estrellas |
| Avance | avances | avances | Entregas de trabajo con idempotencia y revisión |
| Mensaje | mensajes | mensajes | Mensajería directa y grupal en tiempo real |
| Notificacion | notificaciones | notificaciones | Alertas de sistema y Server-Sent Events (SSE) |
| Favorito | favoritos | favoritos | Marcadores reactivos de proyectos |
| Disputa | disputas | disputas | Módulo 10: Arbitraje y mediación de conflictos |
| MensajeDisputa | mensajes_disputa | disputas | Intervenciones en sala de mediación |
| EvidenciaDisputa | evidencias_disputa | disputas | Pruebas documentales de arbitraje |
| LogAuditoria | logs_auditoria | logs | Trazabilidad inmutable de operaciones críticas |

---

## 15. Módulos Avanzados del Sistema

### 15.1 Módulo 8: Contratación Digital y Formalización (`contrataciones`)
El módulo de contratación digital gestiona la transición formal entre la postulación y la ejecución del proyecto:
1. **Negociación Precontractual**: Se establece en la sala de chat de postulación (`en_negociacion`).
2. **Plantilla y Términos**: Se acuerda monto, moneda (COP), forma de pago y cláusulas vinculantes.
3. **Firmas Electrónicas y Criptografía**:
   - `hash_documento`: Hash SHA-256 determinista del contenido contractual congelado en la primera firma para asegurar inmutabilidad jurídica.
   - `hash_contrato`: Hash que incorpora las marcas temporales oficiales de ambas partes.
   - Cada firma genera un registro estricto en `LogAuditoria` con los hashes en `valor_anterior` y `valor_nuevo`.
4. **Expiración Automática**: Las negociaciones sin firma activa expiran automáticamente a los 7 días mediante tarea Celery Beat, comando CLI `expirar_negociaciones` y guarda reactiva JIT.
5. **Revalidación de Vacantes**: Al formalizarse la segunda firma, se ejecuta bloqueo pesimista `select_for_update` sobre el proyecto para impedir sobrecontratación.

### 15.2 Módulo 9: Validación de Identidad y Autenticidad (`usuarios`)
1. **Desarrolladores SENA**:
   - **Padrón Oficial Institucional (`FichaSena`)**: Validación automática contra la lista blanca oficial de fichas administrada por el centro de formación.
   - **Mecanismo de Excepciones (`ExcepcionFichaSena`)**: Habilitación formal y auditada de aprendices con justificación y vigencia temporal.
   - **Pasarela Opcional**: Parámetro `SENA_API_URL` configurado para microservicios institucionales futuros.
2. **Empresas**:
   - **Verificación Documental Oficial Humana**: La empresa aporta soporte legal oficial (RUT / Cámara de Comercio en PDF). El Administrador audita y emite dictamen en el panel (`Empresa Verificada`), auditado en `LogAuditoria`.

### 15.3 Módulo 10: Mediación y Resolución de Disputas (`disputas`)
1. **Apertura de Disputa**: Invocable por la empresa o el desarrollador bajo contratación activa ante causales tipificadas (incumplimiento, abandono, calidad, pago). El proyecto pasa a estado `en_disputa`.
2. **Sala de Mediación Tripartita**:
   - Espacio colaborativo en tiempo real entre empresa, desarrollador y mediador asignado.
   - Comunicación bidireccional vía WebSockets (Django Channels) o fallback HTTP.
   - Auditoría confidencial: cada mensaje enviado genera una traza en `LogAuditoria` (`tabla_afectada='mensajes_disputa'`) sin exponer el contenido del texto.
3. **Resolución Vinculante y Efectos Colaterales**:
   - Al emitir el dictamen vinculante el mediador, el sistema ejecuta automáticamente los efectos colaterales: los avances en revisión se rechazan con el dictamen y los hitos vuelven a `pendiente` para desatascar la continuidad del proyecto.

### 15.4 Tiempo Real, Reportes y Observabilidad
1. **Server-Sent Events (SSE)**: Endpoint `/notificaciones/stream/` con streaming reactivo de notificaciones hacia el navbar del usuario en tiempo real.
2. **WebSockets con Channels y Redis**: Manejo de concurrencia y salas en `/ws/chat/<sala>/` y `/ws/disputas/<id>/`.
3. **Reportes Administrativos CSV**: Generación y descarga bajo demanda de reportes en streaming de proyectos (`/logs/reporte/proyectos/`), aprendices (`/logs/reporte/aprendices/`) y empresas (`/logs/reporte/empresas/`).
4. **Visor de Logs Técnicos**: Endpoint `/logs/tecnico/` protegido para administradores que realiza lectura acotada tipo tail del archivo de logging rotativo del servidor (`var/log/jobdevs.log`), registrando el acceso en `LogAuditoria`.
5. **Tareas en Segundo Plano (Celery & Beat)**: Purga periódica de notificaciones antiguas (`cleanup_notifications`) y expiración de negociaciones vencidas.

### 15.5 Almacenamiento Privado en la Nube con Cloudflare R2 (`usuarios/services_storage.py`)
Para desacoplar el almacenamiento de documentos sensibles (RUT, certificados de Cámara de Comercio, diplomas y actas de grado) de la memoria y disco del servidor web, JobDevs implementa una arquitectura pluggable basada en **Cloudflare R2 (Object Storage S3-compatible)** con **Presigned URLs**:

1. **Ventajas Clave**:
   - **Zero Egress Fees**: Cloudflare R2 no cobra tarifas por transferencia saliente (a diferencia de AWS S3).
   - **Desacoplamiento Total**: Las cargas de archivos pesados no consumen memoria ni hilos de Gunicorn.
   - **Privacidad y Expiración**: Los archivos son 100% privados; el acceso solo es posible mediante tokens criptográficos temporales.

2. **Flujo de Subida Directa (Presigned PUT)**:
   - El cliente solicita una URL de subida a `/api/storage/presigned-upload/` (`api_generar_url_subida_prefirmada`).
   - El servidor valida la sesión y permisos, y genera una URL temporal firmada con validez de 5 minutos (`R2_UPLOAD_URL_EXPIRACION_SEGUNDOS=300`) con prefijo sanitizado `soportes/<rol>/<uuid>_<archivo>`.
   - El navegador sube el archivo directamente hacia Cloudflare R2 vía HTTP PUT.

3. **Flujo de Descarga y Visor Protegido (Presigned GET)**:
   - Los endpoints `/empresa/<id>/documento/` y `/desarrollador/<id>/documento/` validan que el solicitante sea el dueño del documento o un administrador activo.
   - Si R2 está activo (`esta_configurado_r2() == True`), el servidor genera una URL GET temporal firmada con validez de 15 minutos (`R2_DOWNLOAD_URL_EXPIRACION_SEGUNDOS=900`) y redirige al navegador para descarga directa desde la red global de Cloudflare.

4. **Fallback Local Transparente**:
   - En entornos locales de desarrollo, testing automatizado o despliegues sin credenciales R2 configuradas, el servicio degrada automáticamente al almacenamiento local en `/media/` sirviendo los archivos mediante `FileResponse`, garantizando que la suite de pruebas y el desarrollo offline funcionen al 100% sin requerir conexión a internet.

---

## 16. Troubleshooting técnico

**Error: PostgreSQL no conecta desde Django**
1. Verificar que PostgreSQL está corriendo: `systemctl status postgresql` o contenedor `docker compose ps`
2. Verificar credenciales en `.env` (DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT=5432)
3. Verificar estado del servicio: `pg_isready -h localhost -p 5432`

**Error: `Table 'X' doesn't exist`**
Las migraciones no se aplicaron. Ejecutar:
```bash
python manage.py migrate
```

**Error: CSRF token missing en API**
Obtener el token de la cookie de sesión:
```bash
curl -c cookies.txt -d "username=admin&password=..." http://localhost/login/
CSRF=$(grep csrftoken cookies.txt | awk '{print $7}')
```

**Error en tests: `ValueError: DJANGO_SECRET_KEY...`**
Pasar la variable de entorno:
```bash
DJANGO_SECRET_KEY=test-key DJANGO_DEBUG=True pytest -v
```

**Gunicorn workers se reinician constantemente**
Ajustar `--max-requests` y `--max-requests-jitter` en `entrypoint.sh`. Por defecto: 1000 requests por worker con jitter de 50.

---

## 17. Guía de contribución

### 17.1 Agregar una nueva app

```bash
python manage.py startapp nueva_app
```

Luego:
1. Agregar `'nueva_app'` a `INSTALLED_APPS` en `config/settings.py`
2. Crear `models.py` con los modelos
3. Crear `views.py` con las vistas
4. Crear `urls.py` con las rutas
5. Incluir las rutas en `config/urls.py`
6. Crear tests en `nueva_app/tests/`
7. Generar migraciones: `python manage.py makemigrations`

### 16.2 Convenciones de código

- **Idioma:** Código, comentarios y mensajes de commit en español
- **Modelos:** `db_table` explícito en Meta, `related_name` en FKs
- **Vistas:** `@login_required` en toda vista que requiera sesión, `@require_POST` en mutaciones
- **Transacciones:** Usar `transaction.atomic()` en operaciones que modifican múltiples tablas
- **Queries:** Preferir ORM sobre SQL crudo. Usar `select_related()` y `prefetch_related()` para evitar N+1
- **Tests:** Un archivo `test_*.py` por app. Usar fixtures de `conftest.py`

### 16.3 Flujo de trabajo con Git

```bash
git checkout -b feat/nombre-feature
# ... desarrollar ...
git add .
git commit -m "feat(app): descripción breve"
pytest . --ignore=tests/e2e -v  # verificar que todo pase
git push origin feat/nombre-feature
# Crear PR en GitHub
```

### 16.4 Agregar nuevas variables de entorno

1. Agregar la variable en `config/settings.py` con `os.environ.get('NOMBRE', 'default')`
2. Documentarla en `docker/.env.docker.example`
3. Agregarla a la tabla en la sección 11 de este manual
