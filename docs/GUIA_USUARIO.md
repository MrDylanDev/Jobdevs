# Guía de Usuario — JobDevs

> Plataforma de vinculación entre empresas y talento SENA.
> Última actualización: 30 de junio de 2026.

---

## Índice

1. [Roles y acceso](#1-roles-y-acceso)
2. [Registro](#2-registro)
3. [Inicio de sesión](#3-inicio-de-sesión)
4. [Recuperar contraseña](#4-recuperar-contraseña)
5. [Desarrollador](#5-desarrollador)
6. [Empresa](#6-empresa)
7. [Administrador](#7-administrador)
8. [Chat y mensajería](#8-chat-y-mensajería)
9. [Notificaciones](#9-notificaciones)
10. [Preguntas frecuentes](#10-preguntas-frecuentes)

---

## 1. Roles y acceso

JobDevs tiene 3 tipos de usuario:

| Rol | ¿Quién es? | ¿Qué puede hacer? |
|-----|-----------|-------------------|
| **Desarrollador** | Aprendiz o egresado SENA | Postularse a proyectos, trabajar en hitos, chatear, calificar empresas |
| **Empresa** | Organización que necesita software | Publicar proyectos, contratar desarrolladores, revisar avances, calificar |
| **Administrador** | Gestor de la plataforma | Supervisar usuarios y proyectos, activar/suspender cuentas, auditar |

Cada rol tiene su propio dashboard. No se puede acceder al dashboard de otro rol.

---

## 2. Registro

### 2.1 Registro como Desarrollador

1. Ir a la landing page (`/`)
2. Hacer clic en **Registrarse**
3. Seleccionar rol: **Desarrollador**
4. Completar:
   - Username (nombre de usuario único)
   - Nombre completo
   - Tipo de documento: **Cédula de Ciudadanía** (obligatorio para desarrollador)
   - Número de identificación
   - Email (debe ser único)
   - Fecha de nacimiento (debes ser mayor de 18 años)
   - Contraseña (mínimo 8 caracteres, 1 mayúscula, 1 minúscula, 1 número)
5. Hacer clic en **Registrarse**

Al registrarte, iniciás sesión automáticamente y entrás a tu dashboard.

**Importante:** No podés registrarte como desarrollador con NIT. Si seleccionás NIT como tipo de documento, el registro se rechaza.

### 2.2 Registro como Empresa

1. Ir a la landing page (`/`)
2. Hacer clic en **Registrarse**
3. Seleccionar rol: **Empresa**
4. Completar:
   - Username
   - Nombre completo
   - Tipo de documento: **NIT** o **Cédula de Ciudadanía**
   - Número de identificación
   - Email
   - Fecha de nacimiento (mayor de 18 años)
   - Contraseña
5. Hacer clic en **Registrarse**

Una vez registrada, la empresa puede completar su perfil corporativo con logo, sector, teléfono, ciudad y descripción.

---

## 3. Inicio de sesión

1. Ir a la landing page (`/`)
2. Hacer clic en **Iniciar Sesión** (o ir a `/login/`)
3. Seleccionar el rol correcto: **Desarrollador**, **Empresa**, o **Administrador**
4. Ingresar usuario y contraseña
5. Clic en **Ingresar**

**El rol seleccionado DEBE coincidir con tu rol real.** Si sos desarrollador y seleccionás "Empresa", el sistema rechaza el acceso aunque la contraseña sea correcta.

**Seguridad:** Después de 5 intentos fallidos consecutivos, tu cuenta se suspende automáticamente. Contactá al administrador para reactivarla.

**Sesión:** La sesión expira al cerrar el navegador. Si no hacés nada por 1 hora, también expira.

---

## 4. Recuperar contraseña

1. En la landing page, clic en **¿Olvidaste tu contraseña?**
2. Ingresá tu email registrado
3. Recibirás un correo con un enlace de recuperación (válido por 1 hora)
4. Hacé clic en el enlace
5. Ingresá tu nueva contraseña (dos veces)
6. La contraseña se actualiza y podés iniciar sesión

Si tu cuenta estaba suspendida por intentos fallidos, se reactiva automáticamente al restablecer la contraseña.

---

## 5. Desarrollador

### 5.1 Dashboard

Al iniciar sesión ves:

- **Estadísticas personales:** calificación promedio (estrellas), proyectos completados, proyectos activos, favoritos guardados
- **Mis proyectos activos:** contratos vigentes con hitos pendientes y completados
- **Mis postulaciones:** estado de cada postulación (pendiente, aceptada, rechazada)
- **Proyectos finalizados:** historial con calificación recibida
- **Favoritos:** proyectos guardados para postularse después
- **Notificaciones:** últimas 10 alertas del sistema

### 5.2 Buscar y postularse a proyectos

1. Ir a **Proyectos** → **Explorar proyectos**
2. Usar filtros: **Tipo de solución** (Web, Móvil, Automatización, etc.) y **Prioridad** (Alta, Media, Baja)
3. Ver la reputación de la empresa (estrellas) en cada tarjeta de proyecto
4. Clic en **Postularse** en el proyecto deseado
5. Completar: carta de presentación, experiencia, enlace a portafolio
6. Clic en **Enviar postulación**

**Límite:** No podés tener más de 3 postulaciones o proyectos activos simultáneamente. Si ya tenés 3, debés esperar a que alguna se resuelva.

**Duplicados:** No podés postularte dos veces al mismo proyecto.

### 5.3 Favoritos

- Para guardar un proyecto: clic en el ícono de **estrella** en la lista de proyectos
- Para quitarlo: clic otra vez en la misma estrella
- Tus favoritos aparecen en el dashboard, separados de los proyectos donde ya te postulaste
- Solo ves proyectos en estado "publicado". Si el proyecto avanza a otra etapa, desaparece de favoritos

### 5.4 Trabajar en un proyecto

Cuando una empresa acepta tu postulación, el proyecto aparece en **Mis proyectos activos**.

**Ver hitos asignados:**
- En tu dashboard, cada proyecto activo muestra sus hitos (entregables)
- Ves los hitos asignados a tu equipo y los hitos generales del proyecto
- Cada hito tiene estado: Pendiente, En Revisión, Completado

**Registrar un avance:**
1. Ir al proyecto activo
2. Clic en **Registrar Avance**
3. Seleccionar el hito que querés completar
4. Describir lo que hiciste
5. **Obligatorio:** Pegar una URL de evidencia (repositorio, captura, documento)
6. Clic en **Enviar Avance**

El avance queda en estado "Pendiente de Revisión". La empresa lo revisará y lo aceptará o rechazará.

**Si la empresa rechaza tu avance:**
- El hito vuelve a estado "Pendiente"
- Ves el comentario de la empresa explicando qué corregir
- El proyecto vuelve a "En Desarrollo"
- Podés volver a subir el avance corregido

**Cuando todos los hitos están enviados:**
- El proyecto pasa automáticamente a "En Revisión Final"
- La empresa revisa todo y finaliza el proyecto

### 5.6 Editar perfil

Podés mantener actualizado tu perfil profesional desde el dashboard:

1. Ir a **Perfil** → **Editar perfil**
2. Completar o modificar:
   - Foto de perfil
   - Programa de formación (ADSO, etc.)
   - Número de ficha
   - Habilidades (ej: Python, Java, SQL, React...)
   - URL de portafolio (GitHub, LinkedIn, sitio personal)
3. Clic en **Guardar**

### 5.5 Calificar a la empresa

Cuando un proyecto se finaliza, podés calificar a la empresa:

1. Ir al proyecto finalizado
2. Seleccionar puntuación de 1 a 5 estrellas
3. Escribir un comentario (opcional pero recomendado)
4. Clic en **Enviar calificación**

Tu calificación contribuye a la reputación pública de la empresa. Solo podés calificar una vez por proyecto.

---

## 6. Empresa

### 6.1 Dashboard

Al iniciar sesión ves:

- **Estadísticas:** proyectos publicados, activos, postulaciones pendientes, desarrolladores contratados
- **Mis ofertas publicadas:** proyectos en estado "publicado" esperando postulantes
- **Proyectos en desarrollo:** con progreso de hitos y lista de desarrolladores asignados
- **Colaboradores activos:** lista de desarrolladores con contrato vigente
- **Historial:** proyectos finalizados con calificaciones
- **Reputación:** promedio de estrellas recibidas de desarrolladores
- **Notificaciones:** últimas 10 alertas

### 6.2 Publicar un proyecto

1. En el dashboard, clic en **Publicar Proyecto**
2. Completar:
   - Título del proyecto
   - Descripción detallada de lo que necesitás
   - Tipo de solución (Sitio Web, App Móvil, Automatización, Sistema Escritorio, Otro)
   - Prioridad (Alta, Media, Baja)
   - Número de vacantes (cuántos desarrolladores necesitás)
   - Fecha límite (opcional)
3. Clic en **Publicar**

El proyecto se publica inmediatamente y es visible para todos los desarrolladores.

### 6.3 Gestionar postulaciones

1. En el dashboard, clic en **Ver postulaciones** del proyecto
2. Ves cada candidato con: nombre, foto, programa de formación, ficha, habilidades, calificación, proyectos completados, portafolio
3. Para cada postulación podés:
   - **Aceptar:** el desarrollador se contrata automáticamente. Se crea un contrato activo y el proyecto pasa a "En Desarrollo"
   - **Rechazar:** el desarrollador recibe una notificación (no se envía mensaje de rechazo, solo cambia el estado)
   - Dejar en espera para revisar después

**Importante:** Una vez que aceptás una postulación, no se puede deshacer. Asegurate de revisar bien el perfil antes de aceptar.

### 6.4 Crear equipos (opcional, para 2+ desarrolladores)

1. En el proyecto activo, ir a **Gestionar Equipos**
2. Clic en **Crear Equipo**
3. Darle un nombre (ej: "Frontend", "Backend")
4. Seleccionar los miembros del equipo
5. Clic en **Crear**

Los miembros reciben una notificación de que fueron asignados al equipo.

**Eliminar un equipo:**
1. En la lista de equipos del proyecto, clic en **Eliminar** junto al equipo
2. El equipo se elimina inmediatamente
3. Los hitos asignados a ese equipo quedan como hitos generales (sin equipo)

### 6.5 Crear hitos (entregables)

1. En el proyecto activo, ir a **Gestionar Hitos**
2. Completar:
   - Título del hito
   - Descripción de lo que esperás
   - Equipo asignado (opcional — si no seleccionás ninguno, es un hito general para todos)
3. Clic en **Crear Hito**

Los desarrolladores asignados reciben una notificación con la nueva tarea.

**Eliminar un hito:**
1. En la lista de hitos, solo los hitos en estado **Pendiente** muestran el botón **Eliminar**
2. Clic en **Eliminar** junto al hito que ya no necesitás
3. El hito se elimina permanentemente

**No se puede eliminar** un hito que ya está en revisión o completado. Solo hitos pendientes.

### 6.6 Revisar avances

1. En el proyecto activo, ir a **Ver Avances**
2. Ves la lista de avances con:
   - Desarrollador que lo envió
   - Hito asociado
   - Descripción del trabajo
   - **URL de evidencia** (obligatorio para el desarrollador)
   - Fecha y hora
3. Para cada avance:
   - **Aceptar:** opcionalmente escribir un comentario. El hito se marca como completado.
   - **Rechazar:** **obligatorio** escribir un comentario explicando por qué. El hito vuelve a pendiente y el proyecto vuelve a "En Desarrollo".

También ves una barra de progreso con hitos completados / totales.

### 6.7 Finalizar y calificar

Cuando todos los hitos están completados:

1. Ir al proyecto
2. Clic en **Finalizar Proyecto**
3. El sistema te muestra los desarrolladores pendientes de calificar
4. Para cada uno: seleccionar puntuación de 1 a 5 y escribir comentario
5. Cuando todos están calificados, el proyecto se finaliza automáticamente

**No se puede finalizar** un proyecto que tenga hitos sin completar.

Al finalizar, todos los contratos activos se cierran automáticamente y los desarrolladores reciben notificación.

### 6.8 Cancelar / desactivar un proyecto

Si ya no necesitás un proyecto publicado o en desarrollo:

1. En el dashboard, clic en **Desactivar** en el proyecto
2. El proyecto pasa a estado **Inactivo**
3. Todas las postulaciones pendientes se rechazan automáticamente
4. Todos los contratos activos se cancelan
5. Desarrolladores y postulantes reciben notificación

**No se puede desactivar** un proyecto que ya está finalizado.

### 6.9 Editar perfil de empresa

Para mantener tu perfil corporativo actualizado:

1. Ir a **Perfil** → **Editar perfil**
2. Podés modificar:
   - Logo de la empresa
   - Nombre de la empresa
   - Sector (ej: Tecnología, Salud, Educación)
   - Teléfono
   - Ciudad
   - Descripción de la empresa
3. Clic en **Guardar**

El perfil se actualiza inmediatamente. Los desarrolladores ven esta información al explorar tus proyectos.

### 6.10 Gestionar contrataciones

Para ver todos los desarrolladores contratados:

1. Ir a **Contrataciones** en el dashboard
2. Ves la lista de contratos activos con: proyecto, desarrollador, fecha de inicio

**Cancelar un contrato:**
1. En la lista de contrataciones, clic en **Cancelar** en el contrato deseado
2. El contrato pasa a estado "cancelada"
3. Si era el último contrato activo, el proyecto vuelve a "publicado"
4. El desarrollador recibe una notificación

---

## 7. Administrador

### 7.1 Dashboard

El panel administrativo muestra:

- **Estadísticas globales:** total usuarios, total proyectos, proyectos por estado, postulaciones pendientes, promedio de calificación, proyectos retrasados
- **Ranking de talento:** top 5 desarrolladores mejor calificados y top 5 con calificación más baja
- **Ranking de empresas:** top 5 empresas mejor calificadas y top 5 con calificación más baja
- **Lista de usuarios:** últimos 50 registrados, searchable y filtrable
- **Lista de proyectos:** últimos 50, con información de contratos activos e hitos
- **Alertas de retraso:** proyectos sin avances en los últimos 7 días
- **Reseñas recientes:** últimas 10 calificaciones del sistema
- **Logs de auditoría:** últimas 20 acciones registradas
- **Conversaciones:** mensajes con usuarios que contactaron al admin
- **Notificaciones:** alertas del sistema

### 7.2 Gestión de usuarios

**Activar / Suspender usuario individual:**
1. En la lista de usuarios del dashboard, buscar al usuario
2. Clic en el botón de toggle (Activar ↔ Suspender)
3. El cambio es inmediato. Si suspendés a un usuario, no puede iniciar sesión.

**Acciones en lote:**
1. Seleccionar usuarios con los checkboxes
2. Elegir acción: **Activar seleccionados** o **Suspender seleccionados**
3. Clic en **Ejecutar**
4. No podés suspenderte a vos mismo.

### 7.3 API REST administrativa

Endpoints disponibles solo para administradores:

| Método | Endpoint | Acción |
|--------|----------|--------|
| GET | `/api/` | Listar todos los usuarios |
| GET | `/api/<id>/` | Ver detalle de un usuario |
| POST | `/api/crear/` | Crear nuevo usuario |
| PUT | `/api/<id>/actualizar/` | Actualizar usuario (email, nombre, rol, estado) |
| DELETE | `/api/<id>/eliminar/` | Eliminar usuario |
| POST | `/api/bulk-toggle/` | Activar/suspender usuarios en lote |

**Autenticación:** Requiere sesión de administrador + token CSRF en header `X-CSRFToken`.

**Ejemplo cURL:**
```bash
# Login
curl -c cookies.txt -d "username=admin&password=...&rol_seleccionado=administrador" http://localhost/login/

# Extraer CSRF
CSRF=$(grep csrftoken cookies.txt | awk '{print $7}')

# Listar usuarios
curl -b cookies.txt -H "X-CSRFToken: $CSRF" http://localhost/api/
```

### 7.4 Reactivar proyecto finalizado

Si una empresa necesita reabrir un proyecto ya cerrado:
1. Ir al detalle del proyecto
2. Clic en **Reactivar Proyecto**
3. Los contratos finalizados se reactivan

Solo el administrador puede hacer esto. Solo proyectos en estado "finalizado".

### 7.5 Reporte de logs y auditoría

El dashboard incluye acceso a:
- **Historial de estados:** cada cambio de estado de un proyecto queda registrado (quién, cuándo, de qué estado a qué estado)
- **Logs de auditoría:** acciones administrativas (cambios de usuario, cambios de perfil, cancelaciones)
- **Reporte de impresión:** vista imprimible con logs del sistema (`/logs/reporte/`)

---

## 8. Chat y mensajería

### 8.1 Chat grupal del proyecto

Cada proyecto tiene un **Espacio de Trabajo** donde todos los involucrados pueden chatear:

1. Ir al proyecto
2. Clic en **Chat del proyecto** o **Espacio de Trabajo**
3. Escribir mensaje y enviar

Acceso:
- **Empresa:** dueña del proyecto
- **Desarrollador:** solo si tiene contrato (activo o finalizado) con ese proyecto
- **Administrador:** acceso a todos los proyectos

**No se pueden enviar mensajes** en proyectos finalizados (el historial queda visible pero no se puede agregar nuevos).

### 8.2 Chat privado (1 a 1)

1. Ir a **Mensajes** → **Redactar**
2. Seleccionar destinatario (según tu rol, ves diferentes listas):
   - Empresa: ves desarrolladores contratados + administradores
   - Desarrollador: ves empresas con las que tenés contrato + administradores
   - Administrador: ves todos los usuarios
3. Opcionalmente asociar el mensaje a un proyecto
4. Escribir título y contenido
5. Enviar

### 8.3 Bandeja de entrada y enviados

- **Inbox:** mensajes directos que recibiste (`/mensajes/inbox/`)
- **Enviados:** mensajes directos que enviaste (`/mensajes/sent/`)
- **Detalle:** clic en cualquier mensaje para ver la conversación completa

### 8.4 Chat directo desde el dashboard

En el dashboard de administrador, las conversaciones recientes aparecen con indicador de mensajes no leídos. Clic en cualquier conversación para abrir el chat.

---

## 9. Notificaciones

### 9.1 Tipos de notificaciones

| Tipo | ¿Cuándo se genera? |
|------|-------------------|
| Postulación | Un desarrollador se postula a tu proyecto |
| Avance | Un desarrollador completa un hito / Nueva tarea asignada |
| Aprobación | Tu avance fue aceptado / El proyecto fue finalizado |
| Mensaje | Recibiste un mensaje nuevo |
| Alerta | Proyecto cancelado / Postulación rechazada / Cuenta suspendida |

### 9.2 Ver y gestionar notificaciones

En el dashboard de cualquier rol ves las últimas 10 notificaciones con indicador de no leídas.

- Clic en **Marcar todas como leídas** para limpiar el contador
- Las notificaciones persisten en la base de datos incluso después de leídas (histórico)

---

## 10. Preguntas frecuentes

**¿Puedo cambiar mi rol después de registrarme?**
No. El rol se define al registrarse. Si necesitás cambiar, contactá al administrador.

**¿Cuántas postulaciones puedo tener activas?**
Máximo 3 entre postulaciones pendientes y proyectos activos. Si ya tenés 3, no podés postularte a nuevos proyectos hasta que alguno se resuelva.

**¿Puedo editar un proyecto después de publicarlo?**
Actualmente no. Esta funcionalidad está planificada para una versión futura.

**¿Qué pasa si la empresa no revisa mi avance?**
El administrador puede ver proyectos con más de 7 días sin actividad en el dashboard. Si hay demoras, contactá al admin por chat.

**¿Puedo eliminar mi cuenta?**
No desde la plataforma. Contactá al administrador.

**¿La plataforma maneja pagos?**
No. JobDevs facilita la conexión entre empresas y desarrolladores, pero no procesa pagos. El acuerdo económico es entre las partes.

**¿Qué navegadores son compatibles?**
Chrome, Firefox y Edge en sus últimas versiones (y las dos anteriores). En versiones más antiguas puede haber diferencias de estilo. La interfaz está en español.

**¿Cómo reporto un problema o comportamiento inadecuado?**
Usá el chat para contactar al administrador directamente desde tu dashboard.

---

## 11. Cerrar sesión

Para salir de tu cuenta de forma segura:

1. Clic en tu nombre o avatar en la esquina superior
2. Seleccionar **Cerrar sesión**
3. O directamente ir a `/logout/`

La sesión también se cierra automáticamente al cerrar el navegador.

---

## 12. Solución de problemas

**No puedo iniciar sesión.**
Verificá que estás seleccionando el rol correcto (Desarrollador, Empresa o Administrador). Si tu cuenta fue suspendida por intentos fallidos, usá la opción "Recuperar contraseña" para reactivarla.

**Seleccioné el rol equivocado al entrar.**
El sistema te muestra un error. Volvé atrás, seleccioná tu rol real, e intentá de nuevo. No perdés intentos por seleccionar el rol equivocado con la contraseña correcta.

**No veo el botón de postularme a un proyecto.**
Puede ser porque: ya te postulaste antes a ese proyecto, el proyecto ya no acepta postulaciones (estado distinto a "publicado"), o ya tenés 3 postulaciones/proyectos activos.

**La empresa no revisa mi avance hace días.**
El administrador monitorea proyectos con más de 7 días sin actividad. Contactá al admin por chat (`/mensajes/chat/<id_admin>/0/`) para que intervenga.

**No puedo finalizar mi proyecto.**
Verificá que TODOS los hitos estén en estado "completado". Si hay hitos pendientes, no se puede finalizar. Revisá en "Ver Avances" que no quede ninguno sin aprobar.

**Cambié mi perfil pero no se ven los cambios.**
Los cambios son inmediatos. Si no los ves, refrescá la página (F5). Si el problema persiste, revisá que el formulario se haya guardado sin errores.

**Error 404 o página no encontrada.**
Verificá la URL. Si el error persiste, puede ser un enlace roto. Reportalo al administrador.

**Error 500 o "Error interno del servidor".**
Hubo un problema técnico. El administrador puede ver los logs del sistema. Reportá el error indicando qué estabas haciendo cuando ocurrió.
