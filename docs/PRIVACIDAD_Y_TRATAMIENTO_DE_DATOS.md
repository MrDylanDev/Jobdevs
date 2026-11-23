# Privacidad y tratamiento de datos en JobDevs

## 1. Alcance y límite

Esta es una política interna de diseño y operación para el repositorio JobDevs. No sustituye aviso de privacidad, autorización de tratamiento, asesoría jurídica ni las obligaciones aplicables en Colombia. Antes de producción debe ser revisada por el responsable del tratamiento y traducida a textos de consentimiento y atención al titular.

## 2. Principios

- Finalidad: recolectar únicamente lo necesario para operar la vinculación, verificación, contratación, ejecución, mediación y reputación.
- Minimización: no duplicar documentos o mensajes en auditoría, reportes ni notificaciones.
- Acceso mínimo: cada rol accede solo a los recursos que necesita.
- Transparencia: explicar propósito, destinatarios y duración antes de recolectar.
- Exactitud: permitir corrección cuando no afecte evidencia contractual o historial inmutable.
- Conservación limitada: definir y ejecutar plazos por clase de dato.
- Seguridad: cifrado en tránsito, almacenamiento privado, autorización de descarga y rotación de secretos.
- Responsabilidad demostrada: registrar decisiones y accesos sensibles sin copiar el contenido protegido.

## 3. Actores

- Titular: persona o empresa a la que corresponde el dato.
- Empresa: consulta perfiles públicos y evidencia acordada dentro de sus relaciones.
- Desarrollador: consulta sus relaciones, contratos, avances y expedientes.
- Administrador de negocio: revisa verificaciones, disputas y operaciones autorizadas.
- Operador técnico: mantiene infraestructura con acceso excepcional, trazado y limitado.
- Proveedores: correo, almacenamiento, hosting, base de datos y monitoreo conforme a contrato y configuración aprobados.

## 4. Clases de datos

1. Identidad y cuenta: nombre, identificador, email, rol y estado.
2. Perfil profesional/corporativo: programa, ficha, habilidades, portafolio, sector y descripción.
3. Verificación: documentos de empresa, desarrollador, ficha y dictamen humano.
4. Contratación: términos, firmas, timestamps, hashes y evidencia profesional congelada.
5. Ejecución: hitos, descripciones, archivos y URL de avances.
6. Comunicaciones: mensajes privados, chat de proyecto y mediación.
7. Disputas/cancelaciones: causal, relato, evidencia, declaraciones y resolución.
8. Reputación: puntuaciones, comentarios, cantidad y métricas calculadas.
9. Auditoría: actor, acción, recurso, fecha y deltas permitidos.
10. Operación: logs técnicos, métricas, IP cuando sea necesaria y respaldos.

## 5. Reglas de acceso

La fuente operativa es [Matriz de acceso y retención](MATRIZ_ACCESO_Y_RETENCION.md). Reglas transversales:

- Los documentos de verificación se descargan mediante vistas autorizadas.
- La evidencia de disputa es privada para las partes del contrato y administración.
- El administrador no obtiene licencia para divulgar chats o documentos por tener acceso técnico.
- Los archivos privados no se sirven por una ruta pública permanente.
- Las URL prefirmadas son temporales y se tratan como credenciales.
- La suspensión, cancelación o cierre debe reevaluar accesos y conexiones persistentes.
- Los identificadores de URL no sustituyen la autorización de objeto.

## 6. Auditoría sin exposición

Se puede registrar:

- actor o sistema;
- acción;
- tipo de recurso e identificador;
- fecha/hora;
- estado o valor anterior/nuevo no sensible;
- motivo administrativo resumido cuando sea necesario.

Nunca registrar en `LogAuditoria`:

- contraseñas o hashes de contraseña;
- tokens de recuperación, sesión o URL prefirmada;
- claves API/SMTP/R2;
- documento completo o bytes de archivo;
- contenido íntegro de mensajes o mediaciones;
- datos personales no necesarios para identificar el evento.

## 7. Evidencia y archivos

- Validar extensión, tamaño, cabecera y estructura antes de aceptar.
- No confiar en MIME o nombre declarados por el cliente.
- Conservar nombre técnico no predecible y metadatos mínimos.
- Descargar a través de autorización o URL temporal.
- Evitar indexación, caché pública y logs con URL sensible.
- Analizar malware cuando la infraestructura lo permita.
- Registrar quién cargó/asoció el archivo, no duplicar su contenido.

Para disputas se admiten inicialmente PDF, ZIP, PNG y JPG/JPEG hasta 10 MB. Aportar evidencia no determina automáticamente el resultado.

## 8. Comunicaciones

- Chat directo y grupal se limitan a participantes autorizados.
- La mediación es privada para partes y administrador asignado/autorizado.
- El monitoreo administrativo debe tener finalidad explícita y controles operativos.
- La revocación de acceso debe cerrar o revalidar conexiones persistentes.
- No copiar mensajes completos a reportes generales ni auditoría.

## 9. Conservación y eliminación

Los plazos definitivos requieren aprobación jurídica y operativa. Hasta entonces:

- no prometer eliminación automática que el sistema no ejecute;
- marcar cada plazo de la matriz como propuesto, implementado o pendiente;
- preservar contratos, firmas, resoluciones y auditoría mientras exista obligación o disputa;
- eliminar archivos temporales y URL expiradas cuando dejen de ser necesarios;
- incluir respaldos en el procedimiento de expiración, respetando ventanas de recuperación;
- documentar excepciones por litigio, investigación o requerimiento legal.

La eliminación debe considerar base de datos, almacenamiento de objetos, caché, índices, logs y copias. Borrar la fila principal no garantiza por sí solo la desaparición de todas las copias.

## 10. Derechos y solicitudes

Antes de producción se debe habilitar un canal para:

- consulta de datos;
- corrección;
- actualización;
- revocación cuando proceda;
- eliminación cuando no exista obligación de conservación;
- información sobre tratamiento y destinatarios.

Cada solicitud requiere verificación de identidad, alcance, decisión, responsable y fecha. No entregar datos de terceros dentro de exportaciones del solicitante.

## 11. Incidentes

Ante pérdida, acceso indebido o exposición:

1. registrar hora y alcance inicial;
2. preservar evidencia sin divulgarla;
3. limitar acceso y rotar credenciales;
4. identificar clases de datos y titulares afectados;
5. revisar logs y proveedores;
6. activar responsables de seguridad, producto y jurídico;
7. informar según obligaciones aplicables;
8. corregir causa raíz y verificar la mitigación;
9. documentar riesgo residual y acciones preventivas.

## 12. Proveedores y transferencias

Antes de habilitar R2, SMTP, hosting, monitoreo o analítica:

- identificar proveedor, región y subencargados;
- revisar contrato, seguridad y eliminación;
- configurar acceso mínimo y rotación;
- documentar transferencia/transmisión aplicable;
- comprobar borrado y exportación;
- evitar datos reales en servicios de desarrollo como Mailpit.

## 13. Controles previos a producción

- aviso y autorización revisados;
- matriz de retención aprobada;
- TLS y cookies seguras verificados;
- archivos privados no accesibles anónimamente;
- secretos fuera del repositorio;
- backup cifrado/protegido y restauración probada;
- logs sin tokens ni documentos;
- respuesta a incidentes ensayada;
- cuentas administrativas revisadas;
- seguimiento de hallazgos de seguridad actualizado.

## 14. Estado documental

Esta política define el comportamiento esperado. No afirma que todos los controles operativos estén desplegados. Las diferencias se registran en [Seguimiento de hallazgos](SEGUIMIENTO_HALLAZGOS_SEGURIDAD.md) y [Estado de verificación](ESTADO_VERIFICACION_ACTUAL.md).
