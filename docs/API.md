# API Reference — JobDevs

> Endpoints REST disponibles para el panel de administración.
> Base URL: `http://localhost/api/`

---

## Autenticación

Todas las rutas requieren sesión activa con rol `administrador`. Se envía el token CSRF en el header `X-CSRFToken`.

```
Headers:
  Content-Type: application/json
  X-CSRFToken: <token>
```

---

## Usuarios

### Listar todos

```
GET /api/
```

**Respuesta** `200`:
```json
[
  {
    "id": 1,
    "username": "devtest",
    "nombre": "Dev Test",
    "email": "devtest@jobdevs.edu.co",
    "rol": "desarrollador",
    "identificacion": "1234567890"
  }
]
```

**Errores**: `403` si no es admin.

---

### Obtener usuario

```
GET /api/<id>/
```

**Respuesta** `200`:
```json
{
  "id": 1,
  "username": "devtest",
  "nombre": "Dev Test",
  "email": "devtest@jobdevs.edu.co",
  "rol": "desarrollador",
  "identificacion": "1234567890",
  "estado": "activo"
}
```

**Errores**: `403` (no admin), `404` (no existe), `405` (método no GET).

---

### Crear usuario

```
POST /api/crear/
```

**Body**:
```json
{
  "username": "nuevo_dev",
  "email": "nuevo@jobdevs.edu.co",
  "password": "SecurePass123!",
  "rol": "desarrollador"
}
```

**Respuesta** `201`:
```json
{
  "id": 5,
  "status": "created"
}
```

**Validaciones**:
- `username`, `email`, `password`, `rol` son obligatorios
- `rol` debe ser: `desarrollador`, `empresa`, `administrador`
- Email y username deben ser únicos

**Errores**: `400` (campos faltantes, JSON inválido), `403` (no admin), `409` (username/email duplicado).

---

### Actualizar usuario

```
PUT /api/<id>/actualizar/
```

**Body** (todos los campos opcionales):
```json
{
  "email": "nuevo@email.com",
  "nombre": "Nuevo Nombre",
  "rol": "empresa",
  "estado": "suspendido"
}
```

**Respuesta** `200`:
```json
{
  "status": "updated"
}
```

**Efectos secundarios**:
- Si `estado` cambia, se sincroniza `is_active`
- Si `rol` cambia a/desde `administrador`, se invalida caché de admin
- Se registra en `LogAuditoria`

**Errores**: `400` (JSON inválido), `403` (no admin), `405` (no PUT), `409` (email duplicado).

---

### Eliminar usuario

```
DELETE /api/<id>/eliminar/
```

**Respuesta** `200`:
```json
{
  "status": "deleted"
}
```

**Restricciones**:
- No se puede eliminar a uno mismo
- Solo administradores

**Errores**: `400` (auto-eliminación), `403` (no admin), `405` (no DELETE).

---

### Bulk toggle (activar/suspender)

```
POST /api/bulk-toggle/
```

**Body**:
```json
{
  "ids": [1, 2, 3],
  "action": "suspend"
}
```

| `action` | Efecto |
|----------|--------|
| `activate` | `estado='activo'`, `is_active=True` |
| `suspend` | `estado='suspendido'`, `is_active=False` |

**Respuesta** `200`:
```json
{
  "status": "ok",
  "count": 3
}
```

**Restricciones**:
- No se puede suspender al admin que ejecuta la acción
- Solo administradores

**Errores**: `400` (parámetros inválidos, JSON inválido), `403` (no admin), `405` (no POST).

---

## Códigos de error

| Código | Significado |
|--------|------------|
| `200` | Éxito |
| `201` | Creado |
| `400` | Datos inválidos o faltantes |
| `403` | Acceso denegado (no es administrador) |
| `404` | Recurso no encontrado |
| `405` | Método HTTP no permitido |
| `409` | Conflicto (username/email duplicado) |
| `500` | Error interno del servidor |

---

## Ejemplo con cURL

```bash
# Obtener token CSRF
curl -c cookies.txt http://localhost/login/

# Login como admin
curl -b cookies.txt -c cookies.txt \
  -d "username=admin&password=AdminPass123!&rol_seleccionado=administrador" \
  http://localhost/login/

# Extraer token CSRF
CSRF=$(grep csrftoken cookies.txt | awk '{print $7}')

# Listar usuarios
curl -b cookies.txt \
  -H "X-CSRFToken: $CSRF" \
  http://localhost/api/

# Crear usuario
curl -b cookies.txt \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF" \
  -d '{"username":"test","email":"test@jobdevs.edu.co","password":"Test123!","rol":"desarrollador"}' \
  http://localhost/api/crear/

# Suspender usuarios en lote
curl -b cookies.txt \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF" \
  -d '{"ids":[3,4,5],"action":"suspend"}' \
  http://localhost/api/bulk-toggle/
```
