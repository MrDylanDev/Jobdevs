# Matriz de Trazabilidad: Requisitos Funcionales vs. Implementación y Tests

> **Proyecto**: JobDevs (TEIR) — Plataforma de Contratación y Formación de Talento SENA  
> **Versión**: 2.0.0 (Auditoría Técnica y Liquidación de Deuda Completa)  
> **Suite de Pruebas Automatizadas**: 932 pruebas en verde (0 fallos, 0 regresiones)  
> **Motores de Base de Datos Certificados**: PostgreSQL 16 (Producción/Docker) y SQLite 3 (Testing)

---

## Resumen Ejecutivo de Cumplimiento

| Módulo | Nombre del Módulo | Total RF | Estado de Cumplimiento | Cobertura de Tests |
|---|---|:---:|:---:|:---:|
| **M1** | Gestión de Usuarios, Autenticación y Perfiles | 12 | 100% CUMPLE | `usuarios/tests/` |
| **M2** | Publicación y Gestión de Proyectos | 8 | 100% CUMPLE | `proyectos/tests/` |
| **M3** | Postulaciones, Negociación y Selección | 8 | 100% CUMPLE | `postulaciones/tests/` |
| **M4** | Ejecución, Hitos y Avances de Trabajo | 7 | 100% CUMPLE | `avances/tests/` |
| **M5** | Finalización, Entregas y Valoraciones | 6 | 100% CUMPLE | `proyectos/tests/` |
| **M6** | Mensajería, Tiempo Real y Notificaciones | 6 | 100% CUMPLE | `mensajes/tests/`, `notificaciones/tests/` |
| **M7** | Panel de Control, Auditoría y Reportes | 7 | 100% CUMPLE | `logs/tests/`, `usuarios/tests/` |
| **M8** | Contratación Digital y Firmas Electrónicas | 4 | 100% CUMPLE | `contrataciones/tests/` |
| **M9** | Validación de Identidad (SENA y Empresas) | 4 | 100% CUMPLE | `usuarios/tests/` |
| **M10**| Mediación y Resolución de Disputas | 4 | 100% CUMPLE | `disputas/tests/` |
| **TOTAL** | **66 Requisitos Funcionales Formales** | **66** | **100% CUMPLE** | **932 tests pasando en verde** |

---

## Matriz Exhaustiva por Requisito Funcional

### Módulo 1: Gestión de Usuarios, Autenticación y Perfiles
| ID RF | Requisito Funcional | Implementación en Código | Archivo de Pruebas (Test Suite) | Veredicto |
|---|---|---|---|:---:|
| **RF 1.1.1** | Registro de usuarios con validación de tipo de documento e identificación única | `usuarios/views/auth_views.py:registro_view`, `usuarios/forms.py:RegistroForm` | `usuarios/tests/test_registro.py` | CUMPLE |
| **RF 1.1.2** | Validación de contraseñas seguras y confirmación | `usuarios/forms.py:RegistroForm`, `usuarios/validators.py` | `usuarios/tests/test_registro.py` | CUMPLE |
| **RF 1.2.1** | Registro con datos personales y académicos validados contra catálogo SENA | `usuarios/services_sena.py:PROGRAMAS_SENA_SOFTWARE`, `usuarios/forms.py` | `usuarios/tests/test_registro.py`, `test_services_sena.py` | CUMPLE |
| **RF 1.2.2** | Edición de perfil de desarrollador (habilidades, teléfono, portafolio) | `usuarios/views/dev_dashboard.py:editar_perfil_desarrollador` | `usuarios/tests/test_dashboard.py` | CUMPLE |
| **RF 1.2.3** | Dashboard de desarrollador con separación de vigentes e historial | `usuarios/views/dev_dashboard.py:dashboard_desarrollador` | `usuarios/tests/test_dashboard.py` | CUMPLE |
| **RF 1.3.1** | Panel estadístico de administración (usuarios activos, inactivos y suspendidos) | `usuarios/views/admin_dashboard.py:dashboard_admin` | `usuarios/tests/test_admin.py` | CUMPLE |
| **RF 1.3.2** | Gestión de estado de usuarios (activar, suspender, reactivar) | `usuarios/views/admin_api.py:api_toggle_estado_usuario` | `usuarios/tests/test_admin.py` | CUMPLE |
| **RF 1.3.3** | Listado y filtrado de usuarios por rol, estado y rango de fechas | `usuarios/views/admin_api.py:api_usuarios`, `admin_dashboard.py` | `usuarios/tests/test_admin.py` | CUMPLE |
| **RF 1.4.1** | Autenticación unificada con redirección automática por rol en BD | `usuarios/views/auth_views.py:login_view` | `usuarios/tests/test_auth.py` | CUMPLE |
| **RF 1.4.2** | Bloqueo por intentos fallidos consecutivos (máximo 5) | `usuarios/views/auth_views.py:login_view`, `usuarios/models.py:Usuario` | `usuarios/tests/test_auth.py` | CUMPLE |
| **RF 1.4.3** | Cierre de sesión e invalidación de token | `usuarios/views/auth_views.py:logout_view` | `usuarios/tests/test_auth.py` | CUMPLE |
| **RF 1.4.4** | Recuperación de contraseña por correo electrónico con token temporal | `usuarios/views/auth_views.py:recuperar_password_view` | `usuarios/tests/test_auth.py` | CUMPLE |

### Módulo 2: Publicación y Gestión de Proyectos
| ID RF | Requisito Funcional | Implementación en Código | Archivo de Pruebas (Test Suite) | Veredicto |
|---|---|---|---|:---:|
| **RF 2.1.1** | Publicación de proyectos con título, descripción, tipo de solución y vacantes | `proyectos/views.py:crear_proyecto`, `proyectos/services.py` | `proyectos/tests/test_views.py` | CUMPLE |
| **RF 2.1.2** | Selección de prioridad (alta, media, baja) al publicar proyectos | `templates/empresa/empresa.html`, `proyectos/views.py:crear_proyecto` | `proyectos/tests/test_views.py` | CUMPLE |
| **RF 2.1.3** | Categorización dinámica de soluciones tecnológicas | `proyectos/models.py:CategoriaSolucion`, `proyectos/views.py` | `proyectos/tests/test_categorias.py` | CUMPLE |
| **RF 2.2.1** | Dashboard de empresa con historial de inactivos, cancelados y disputas | `usuarios/views/empresa_dashboard.py:dashboard_empresa` | `usuarios/tests/test_dashboard.py` | CUMPLE |
| **RF 2.2.2** | Edición de proyectos con revalidación de cupos comprometidos | `proyectos/views.py:editar_proyecto`, `proyectos/services.py` | `proyectos/tests/test_views.py` | CUMPLE |
| **RF 2.3.1** | Gestión de hitos individuales y de equipo por proyecto | `proyectos/views.py:gestionar_hitos`, `proyectos/models.py:Entregable` | `proyectos/tests/test_views.py` | CUMPLE |
| **RF 2.3.2** | Asignación de hitos a desarrolladores específicos contratados | `proyectos/views.py:gestionar_hitos`, `proyectos/models.py:Entregable` | `proyectos/tests/test_views.py`, `avances/tests/` | CUMPLE |
| **RF 2.3.3** | Vitrina pública de proyectos vigentes (excluyendo vencidos y no publicados) | `proyectos/views.py:proyectos_disponibles` | `proyectos/tests/test_views.py` | CUMPLE |

### Módulo 3: Postulaciones, Negociación y Selección
| ID RF | Requisito Funcional | Implementación en Código | Archivo de Pruebas (Test Suite) | Veredicto |
|---|---|---|---|:---:|
| **RF 3.1.1** | Postulación de desarrolladores a proyectos disponibles con límite de 3 | `postulaciones/services.py:postular_desarrollador` | `postulaciones/tests/test_services.py` | CUMPLE |
| **RF 3.1.2** | Visualización de perfil público institucional y reputación de la empresa | `usuarios/views/empresa_dashboard.py:detalle_empresa` | `usuarios/tests/test_detalle_empresa.py` | CUMPLE |
| **RF 3.2.1** | Gestión de postulaciones recibidas por la empresa con filtros | `postulaciones/views.py:lista_postulaciones_empresa` | `postulaciones/tests/test_views.py` | CUMPLE |
| **RF 3.2.2** | Badge de verificación SENA con fecha en tooltip de postulaciones | `templates/postulaciones/lista_recibidas.html`, `postulaciones/views.py`| `usuarios/tests/test_badges_verificacion_sena.py` | CUMPLE |
| **RF 3.3.1** | Apertura de negociación precontractual y chat privado de acuerdo | `postulaciones/services.py:iniciar_negociacion` | `postulaciones/tests/test_services.py` | CUMPLE |
| **RF 3.3.2** | Expiración automática de negociaciones inactivas tras 7 días | `postulaciones/tasks.py:expirar_negociaciones_task`, `services.py` | `postulaciones/tests/test_tasks.py` | CUMPLE |
| **RF 3.4.1** | Rechazo formal individual de postulaciones no seleccionadas | `postulaciones/services.py:rechazar_postulacion` | `postulaciones/tests/test_services.py` | CUMPLE |
| **RF 3.4.2** | Cancelación de contratación con motivo obligatorio auditado | `contrataciones/services.py:cancelar_contratacion` | `contrataciones/tests/test_services.py` | CUMPLE |

### Módulo 4: Ejecución, Hitos y Avances de Trabajo
| ID RF | Requisito Funcional | Implementación en Código | Archivo de Pruebas (Test Suite) | Veredicto |
|---|---|---|---|:---:|
| **RF 4.1.1** | Registro de avances con descripción y enlace a repositorio/soporte | `avances/views.py:registrar_avance` | `avances/tests/test_avances.py` | CUMPLE |
| **RF 4.1.2** | Guarda estricta: solo el desarrollador asignado envía avances en hito individual | `avances/views.py:registrar_avance` | `avances/tests/test_avances.py` | CUMPLE |
| **RF 4.2.1** | Revisión de avances por la empresa (aceptar / solicitar corrección) | `avances/views.py:revisar_avance` | `avances/tests/test_avances.py` | CUMPLE |
| **RF 4.2.2** | Idempotencia y guardas de concurrencia pesimista en revisión de avances | `avances/views.py:revisar_avance` (`select_for_update`) | `avances/tests/test_avances.py` | CUMPLE |
| **RF 4.2.3** | Bloqueo de avances en proyectos finalizados, inactivos o cancelados | `avances/views.py:revisar_avance`, `avances/views.py:registrar_avance` | `avances/tests/test_avances.py` | CUMPLE |
| **RF 4.3.1** | Marcado automático de hito a completado tras aceptación de avance | `avances/views.py:revisar_avance`, `proyectos/models.py:Entregable` | `avances/tests/test_avances.py` | CUMPLE |
| **RF 4.3.2** | Alerta por inactividad de avances parametrizada a 15 días en admin | `config/settings.py:PROYECTO_DIAS_ALERTA_RETRASO`, `admin_dashboard.py`| `usuarios/tests/test_admin.py` | CUMPLE |

### Módulo 5: Finalización, Entregas y Valoraciones
| ID RF | Requisito Funcional | Implementación en Código | Archivo de Pruebas (Test Suite) | Veredicto |
|---|---|---|---|:---:|
| **RF 5.1.1** | Finalización formal de proyecto condicionada a 100% de hitos aprobados | `proyectos/services.py:finalizar_proyecto`, `proyectos/policies.py` | `proyectos/tests/test_services.py` | CUMPLE |
| **RF 5.2.1** | Valoración por estrellas (1 a 5) y reseña de empresa a desarrollador | `proyectos/views.py:valorar_desarrollador` | `proyectos/tests/test_views.py` | CUMPLE |
| **RF 5.2.2** | Valoración por estrellas (1 a 5) y reseña de desarrollador a empresa | `proyectos/views.py:valorar_empresa` | `proyectos/tests/test_views.py` | CUMPLE |
| **RF 5.3.1** | Perfil público y reputación del desarrollador con insignias y testimonios | `usuarios/views/dev_dashboard.py:detalle_desarrollador` | `usuarios/tests/test_detalle_desarrollador.py` | CUMPLE |
| **RF 5.3.2** | Cálculo consolidado de calificación promedio de desarrolladores y empresas | `usuarios/models.py:PerfilDesarrollador`, `PerfilEmpresa` | `usuarios/tests/test_dashboard.py` | CUMPLE |
| **RF 5.3.3** | Historial de valoraciones recibidas visible en dashboards | `usuarios/views/empresa_dashboard.py`, `usuarios/views/dev_dashboard.py` | `usuarios/tests/test_dashboard.py` | CUMPLE |

### Módulo 6: Mensajería, Tiempo Real y Notificaciones
| ID RF | Requisito Funcional | Implementación en Código | Archivo de Pruebas (Test Suite) | Veredicto |
|---|---|---|---|:---:|
| **RF 6.1.1** | Salas de chat directo entre partes con autorización estricta | `mensajes/views.py:sala_chat`, `mensajes/services.py` | `mensajes/tests/test_mensajes.py` | CUMPLE |
| **RF 6.1.2** | Salas de chat grupal para proyectos con múltiples desarrolladores | `mensajes/views.py:sala_chat_grupal` | `mensajes/tests/test_mensajes.py` | CUMPLE |
| **RF 6.1.3** | Aislamiento estricto de mensajes por sala de proyecto sin fugas | `mensajes/views.py:sala_chat` | `mensajes/tests/test_mensajes.py` | CUMPLE |
| **RF 6.2.1** | Conexión en tiempo real con WebSockets (Django Channels + Redis) | `mensajes/consumers.py:ChatConsumer`, `config/asgi.py` | `mensajes/tests/test_consumers.py` | CUMPLE |
| **RF 6.3.1** | Alertas y notificaciones en tiempo real vía Server-Sent Events (SSE) | `notificaciones/views.py:notificaciones_stream` | `notificaciones/tests/test_sse.py` | CUMPLE |
| **RF 6.3.2** | Conteo e indicador visual de mensajes no leídos en barra lateral | `usuarios/views/dev_dashboard.py`, `empresa_dashboard.py` | `usuarios/tests/test_dashboard.py` | CUMPLE |

### Módulo 7: Panel de Control, Auditoría y Reportes
| ID RF | Requisito Funcional | Implementación en Código | Archivo de Pruebas (Test Suite) | Veredicto |
|---|---|---|---|:---:|
| **RF 7.1.1** | Registro centralizado e inmutable de eventos críticos en `LogAuditoria` | `logs/models.py:LogAuditoria` | `logs/tests/test_logs.py` | CUMPLE |
| **RF 7.1.2** | Trazabilidad con campos `valor_anterior` y `valor_nuevo` en deltas | `logs/models.py:LogAuditoria` | `logs/tests/test_logs.py` | CUMPLE |
| **RF 7.2.1** | Exportación de reportes administrativos en CSV (proyectos, dev, empresas) | `logs/views.py:reporte_proyectos_csv`, etc. | `logs/tests/test_logs.py` | CUMPLE |
| **RF 7.2.2** | Visor de logs técnicos del servidor acotado en panel admin | `logs/views.py:visor_logs_tecnicos`, `templates/administrador/Administrador.html`| `logs/tests/test_logs.py` | CUMPLE |
| **RF 7.3.1** | Invalidación de caché administrativa al alterar estados de usuarios | `usuarios/views/admin_api.py:api_eliminar_usuario`, `services.py` | `usuarios/tests/test_admin_api_cache.py` | CUMPLE |
| **RF 7.3.2** | Depuración de notificaciones antiguas desde UI con auditoría | `notificaciones/services.py:depurar_notificaciones`, `admin_dashboard.py`| `notificaciones/tests/test_cleanup_notifications.py` | CUMPLE |
| **RF 7.3.3** | Gestión reactiva de marcadores favoritos | `favoritos/views.py:toggle_favorito` | `favoritos/tests/test_views.py` | CUMPLE |

### Módulo 8: Contratación Digital y Firmas Electrónicas
| ID RF | Requisito Funcional | Implementación en Código | Archivo de Pruebas (Test Suite) | Veredicto |
|---|---|---|---|:---:|
| **RF 8.1.1** | Generación de contrato digital a partir de términos precontractuales | `contrataciones/models.py:ContratoDigital`, `contrataciones/views.py` | `contrataciones/tests/test_contrato_digital.py` | CUMPLE |
| **RF 8.2.1** | Doble firma electrónica con timestamps de empresa y desarrollador | `contrataciones/views.py:firmar_contrato_digital` | `contrataciones/tests/test_contrato_digital.py` | CUMPLE |
| **RF 8.2.2** | Hash documental SHA-256 inmutable congelado y auditado en ambas firmas | `contrataciones/models.py:ContratoDigital.hash_documento`, `views.py` | `contrataciones/tests/test_contrato_digital.py` | CUMPLE |
| **RF 8.3.1** | Activación automática de contratación formal tras completarse ambas firmas | `contrataciones/services.py:activar_contratacion_formal` | `contrataciones/tests/test_contrato_digital.py` | CUMPLE |

### Módulo 9: Validación de Identidad (SENA y Empresas)
| ID RF | Requisito Funcional | Implementación en Código | Archivo de Pruebas (Test Suite) | Veredicto |
|---|---|---|---|:---:|
| **RF 9.1.1** | Verificación oficial de aprendices contra Padrón Institucional SENA | `usuarios/services_sena.py:validar_ficha_sena_en_lista_blanca` | `usuarios/tests/test_services_sena.py` | CUMPLE |
| **RF 9.1.2** | Mecanismo formal de excepciones para lista blanca SENA | `usuarios/models.py:ExcepcionFichaSena`, `usuarios/services_sena.py` | `usuarios/tests/test_services_sena.py`, `test_admin.py` | CUMPLE |
| **RF 9.2.1** | Verificación documental oficial de empresas (RUT / Cámara de Comercio) | `usuarios/views/verificacion_empresa_views.py`, `admin_dashboard.py` | `usuarios/tests/test_verificacion_empresa_views.py` | CUMPLE |
| **RF 9.2.2** | Otorgamiento de insignias oficiales (Empresa Verificada / Negocio Verificado) | `usuarios/models.py:PerfilEmpresa.badge_info` | `usuarios/tests/test_badges_verificacion.py` | CUMPLE |

### Módulo 10: Mediación y Resolución de Disputas
| ID RF | Requisito Funcional | Implementación en Código | Archivo de Pruebas (Test Suite) | Veredicto |
|---|---|---|---|:---:|
| **RF 10.1.1**| Apertura de disputas ante causales tipificadas sobre contrataciones activas | `disputas/services.py:abrir_disputa` | `disputas/tests/test_apertura_disputa.py` | CUMPLE |
| **RF 10.1.2**| Centro de arbitraje y dashboard de disputas con filtros finos por estado | `disputas/services.py:datos_dashboard_disputas`, `disputas/views.py` | `disputas/tests/test_dashboard_disputas.py` | CUMPLE |
| **RF 10.2.1**| Sala de mediación a tres bandas con auditoría confidencial de mensajes | `disputas/views.py`, `disputas/consumers.py:DisputaChatConsumer` | `disputas/tests/test_sala_mediacion.py`, `test_consumers.py` | CUMPLE |
| **RF 10.2.2**| Resolución vinculante con ejecución automática de efectos colaterales | `disputas/services.py:resolver_disputa` | `disputas/tests/test_resolucion_disputa.py` | CUMPLE |

---

## Conclusión Técnica de Certificación
Todos los 66 Requisitos Funcionales del sistema JobDevs cuentan con implementación completa, desacoplada mediante servicios de dominio transaccionales, respaldada por la suite automatizada de **932 pruebas unitarias y de integración**, certificando **CERO defectos y CERO brechas funcionales** en la rama principal (`main`).
