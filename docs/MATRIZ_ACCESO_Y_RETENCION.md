# Matriz de acceso y retención de datos

## Convenciones

- **Implementado:** existe un control local identificado; requiere verificación de despliegue cuando corresponda.
- **Parcial:** existe control, pero falta cobertura o gobierno operativo.
- **Pendiente:** política o automatización no demostrada.
- Los plazos de retención marcados como «por aprobar» no deben presentarse a usuarios como garantía automática.

| Clase de dato | Titular/creador | Lectores autorizados | Almacenamiento | Retención | Eliminación/anonimización | Estado |
|---|---|---|---|---|---|---|
| Cuenta e identidad | Usuario | Propio usuario; administración por función | PostgreSQL | Por aprobar; mientras cuenta/obligaciones estén activas | Flujo de baja sujeto a contratos, auditoría y obligaciones | Parcial |
| Perfil profesional público | Desarrollador | Público según superficie | PostgreSQL/media | Mientras el perfil sea publicado y por plazo histórico aprobado | Ocultar/actualizar; separar historial contractual congelado | Parcial |
| Perfil corporativo público | Empresa | Público según superficie | PostgreSQL/media | Mientras el perfil sea publicado y por plazo histórico aprobado | Ocultar/actualizar; preservar contratos necesarios | Parcial |
| Documento de verificación | Empresa/desarrollador | Titular y administración autorizada | Media/R2 según entorno | Por aprobar; solo mientras sea necesario para acreditar revisión | Borrar almacenamiento y referencia; considerar respaldos | Control de descarga implementado; retención pendiente |
| Ficha/excepción SENA | Desarrollador/administración | Propio usuario y administración; datos públicos mínimos | PostgreSQL | Mientras verificación esté vigente + histórico aprobado | Revocar/anonimizar justificación sensible cuando proceda | Parcial |
| Postulación y carta | Desarrollador | Desarrollador, empresa titular y administración por función | PostgreSQL | Ciclo del proyecto + plazo por aprobar | Anonimizar o eliminar cuando no exista obligación | Pendiente de política |
| Evidencia profesional congelada | Partes del contrato | Partes y administración autorizada | Contrato digital/PostgreSQL | Vida contractual + plazo legal/defensa aprobado | No alterar firma histórica; anonimizar solo con criterio jurídico | Implementado a nivel de aplicación |
| Contrato, firmas y hashes | Ambas partes | Partes y administración autorizada | PostgreSQL | Plazo contractual/legal por aprobar | Preservar integridad; eliminación sujeta a obligación | Implementado localmente |
| Descripción de avance | Desarrollador | Partes del proyecto y administración por función | PostgreSQL | Ciclo del proyecto + histórico aprobado | Anonimizar si deja de ser necesaria | Parcial |
| Archivo/URL de avance | Desarrollador | Partes autorizadas del proyecto | Media/R2 | Por aprobar | Eliminar objeto y referencia, incluida expiración de URL | Riesgo histórico de exposición; ver seguimiento |
| Mensaje privado | Remitente/receptor | Participantes; administración solo con finalidad autorizada | PostgreSQL | Por aprobar | Eliminar/anonimizar según obligaciones y disputas | Acceso aplicativo; gobierno pendiente |
| Chat grupal | Participantes del proyecto | Participantes vigentes y administración autorizada | PostgreSQL/Channels | Por aprobar | Revocar acceso y aplicar política aprobada | Revalidación de conexiones pendiente de verificar |
| Mensaje de mediación | Partes/admin | Participantes de la disputa | PostgreSQL/Channels | Expediente + plazo aprobado | Preservar expediente; anonimizar cuando legalmente proceda | Privacidad local implementada/parcial |
| Evidencia de disputa | Parte que aporta | Ambas partes y administración | Media privada | Expediente + plazo por aprobar | Borrar objeto/referencia cuando expire obligación | Descarga autorizada implementada |
| Declaración de indisponibilidad | Parte que declara | Partes y administración | PostgreSQL | Expediente + plazo aprobado | Mismo tratamiento del expediente | Implementado localmente |
| Solicitud de cancelación | Parte solicitante | Partes y administración por función | PostgreSQL | Contrato/expediente + plazo aprobado | Preservar decisión; anonimizar cuando proceda | Parcial |
| Valoración y comentario | Evaluador/destinatario | Público según perfil y administración | PostgreSQL | Histórico de reputación por aprobar | Inmutabilidad de aplicación; política de anonimización pendiente | Parcial |
| Métricas de reputación | Sistema | Público según superficie; administración | Calculado/PostgreSQL | Mientras existan valoraciones y configuración | Recalcular tras cambios válidos de fuente | Integración uniforme pendiente |
| Log de auditoría | Sistema/actor | Administración autorizada y operación limitada | PostgreSQL | Plazo de seguridad/legal por aprobar | Inmutable por API; purga controlada aún no definida | Implementado a nivel de modelo; retención pendiente |
| Log técnico | Sistema | Operación/admin autorizado | Archivos/stream del entorno | Ventana operativa por aprobar | Rotación y borrado seguro | Parcial |
| Notificación | Sistema | Destinatario y administración por función | PostgreSQL | Ventana funcional por aprobar | Depuración autorizada | Implementado parcialmente |
| Respaldo | Sistema/operación | Operación autorizada | Volumen/almacenamiento externo | 7 días diarios; semanal hasta 30 días según configuración actual | Retención automatizada; destrucción del medio externo por definir | Implementado localmente, entorno real no verificado |
| URL prefirmada/token | Sistema | Destinatario técnico temporal | Memoria/logs evitados | Solo vigencia técnica | Expiración; no persistir ni auditar contenido | Política; R2 real no verificado |

## Reglas de revisión

1. Cualquier nueva tabla o archivo debe incorporarse a esta matriz.
2. El plazo definitivo requiere aprobación del responsable del tratamiento.
3. La implementación de una purga debe probar destinatarios, dependencias, respaldos, idempotencia y auditoría.
4. Un expediente bajo disputa, investigación o requerimiento legal puede suspender temporalmente la eliminación; la excepción debe quedar justificada.
5. Los derivados analíticos deben rastrearse hasta su fuente para recalcular o eliminar cuando proceda.
6. Revisar la matriz antes de cada despliegue que añada datos, proveedores o integraciones.
