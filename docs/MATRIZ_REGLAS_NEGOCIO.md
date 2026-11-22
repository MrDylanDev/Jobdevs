# Matriz de reglas de negocio — JobDevs

## 1. Propósito y alcance

Esta matriz consolida las reglas que gobiernan decisiones, permisos, estados, cálculos y efectos de negocio de JobDevs. No reemplaza la matriz oficial de requisitos funcionales ni la matriz de requisitos no funcionales.

Fuentes relacionadas:

- matriz oficial de RF: `../Documentación JobDevs/Matriz_de_Requisitos_JobDevs_VERIFICADA.xlsx`;
- matriz de RNF: `../Documentación JobDevs/Matriz_RNF_JobDevs.xlsx`;
- [conciliación de RF](CONCILIACION_RF_BASE.md);
- [trazabilidad de requisitos](TRAZABILIDAD_REQUISITOS.md);
- [decisiones de producto aprobadas](DECISIONES_PRODUCTO_APROBADAS.md);
- código y pruebas relacionados indicados en cada fila.

Una prueba relacionada no demuestra necesariamente toda la regla. Los estados de esta matriz significan:

- **Implementada localmente:** se localizó una ruta autoritativa y prueba relacionada.
- **Parcial:** existe implementación, pero falta una parte, una superficie o evidencia de infraestructura/aceptación.
- **Decisión aprobada:** la política está aprobada; su implementación completa se evalúa por separado.
- **Brecha:** el comportamiento requerido no está implementado o no tiene política aprobada suficiente.

## 2. Convenciones

| Prefijo | Dominio |
|---|---|
| `RN-USR` | Usuarios, autenticación y perfiles |
| `RN-ADM` | Administración y auditoría |
| `RN-PROY` | Proyectos y vacantes |
| `RN-POST` | Postulaciones y negociación |
| `RN-CON` | Contrato digital y contratación |
| `RN-AVA` | Hitos y avances |
| `RN-DIS` | Cancelación, disputas y evidencia |
| `RN-VAL` | Finalización, valoraciones y reputación |
| `RN-MSG` | Mensajería |
| `RN-NOT` | Notificaciones |
| `RN-ARC` | Archivos y almacenamiento |
| `RN-FAV` | Favoritos |
| `RN-OPS` | Operación, respaldo y retención |

## 3. Usuarios, autenticación y perfiles

| ID | Regla normativa | Actor y precondición | Resultado o rechazo | Implementación autoritativa | Prueba relacionada | Origen | Estado y límite |
|---|---|---|---|---|---|---|---|
| RN-USR-01 | El registro solo admite empresa o desarrollador y crea el perfil del rol. | Visitante; formulario válido. | Crea usuario, inicia sesión y dirige al dashboard del rol; formulario inválido no crea cuenta. | `usuarios/views/registration_views.py::registro_view`; `usuarios/forms.py::RegistroUsuarioForm.save` | `usuarios/tests/test_registro.py` | RF 1.1.1, 1.1.4, 1.2.1 y 1.2.4 | Implementada localmente; el modelo no limita por sí solo todos los roles posibles. |
| RN-USR-02 | La persona registrada debe ser mayor de edad. | Visitante con fecha de nacimiento. | Menor de 18 años: rechazo. | `RegistroUsuarioForm.clean_fecha_nacimiento` | `test_registro_underage` | RF 1.1.1 y 1.2.1 | Implementada en formulario; una escritura ORM directa puede omitirla. |
| RN-USR-03 | Correo e identificación deben ser únicos; el correo se normaliza a minúsculas. | Registro de usuario. | Duplicado: error; si falta username, se usa el correo normalizado. | `usuarios/models.py::Usuario`; `RegistroUsuarioForm.clean_email`, `clean_identificacion` | Pruebas de duplicados en `test_registro.py` | RF 1.1.1 y 1.2.1 | Implementada localmente; identificación admite vacío para registros legados. |
| RN-USR-04 | Un desarrollador no puede usar NIT y sus datos SENA deben ser válidos y coherentes. | Registro con rol desarrollador. | NIT, programa inválido o programa incompatible con ficha activa: rechazo. | `RegistroUsuarioForm.clean`; `usuarios/services_sena.py` | Pruebas de registro y `test_services_sena.py` | RF 9.1.1 | Implementada en los flujos inspeccionados. |
| RN-USR-05 | Ficha/programa SENA pueden verificarse automáticamente contra la lista blanca; las excepciones requieren revisión auditada. | Desarrollador con ficha/programa o solicitud manual. | Coincidencia activa verifica; excepción o soporte pasa por decisión administrativa. | `usuarios/services_sena.py`; `FichaSena`; `ExcepcionFichaSena` | Pruebas SENA y administración | RF 9.1.1, 9.1.2; RF-N10, N12 | Implementada localmente; no demuestra consulta en vivo a SOFIA Plus. |
| RN-USR-06 | El login es unificado: autentica por username o correo sin distinguir mayúsculas y usa el rol persistido. | Credenciales válidas; cuenta activa. | Redirección por rol real; un rol enviado por el cliente no altera permisos. | `usuarios/backends.py::UsuarioAuthBackend`; `usuarios/views/auth_views.py::login_view` | `usuarios/tests/test_auth.py` | Excepción aprobada a RF 1.4.1; RF 1.4.4 | Implementada localmente. |
| RN-USR-07 | Cinco contraseñas incorrectas consecutivas suspenden la cuenta sin revelar existencia ni conteo. | Login inválido de una cuenta conocida. | Quinto fallo: `suspendido`, `is_active=False`, bloqueo por intentos; mensaje genérico. | `login_view` | Pruebas de bloqueo y anti-enumeración | RF 1.4.2; RNF-01, 17 | Implementada localmente; no hay desbloqueo automático por tiempo. |
| RN-USR-08 | Una cuenta inactiva o suspendida no puede iniciar ni conservar una sesión utilizable. | Usuario inactivo/suspendido. | Login rechazado; sesión restaurada se invalida o el middleware expulsa. | `UsuarioAuthBackend.user_can_authenticate`; `UsuarioActivoMiddleware` | `test_auth.py`; `test_middleware.py` | RF 1.3.2; RNF-20, 37 | Implementada en rutas cubiertas por backend/middleware. |
| RN-USR-09 | La recuperación usa token aleatorio, guarda solo su SHA-256, expira en una hora y es de un uso. | Correo registrado; token vigente. | Cambia contraseña, consume token e invalida sesiones. | `recuperar_view`; `restablecer_view`; `invalidar_sesiones_activas_usuario` | Pruebas de recuperación en `test_auth.py` | RF interno 1.4.4; RNF-16, 18, 19 | Parcial: lógica localizada; el envío de correo requiere reverificación del entorno. |
| RN-USR-10 | Restablecer contraseña solo reactiva suspensiones causadas por intentos; una suspensión administrativa se conserva. | Token válido. | Bloqueo por intentos se limpia; suspensión administrativa permanece. | `restablecer_view` | Pruebas `test_restablecer_*suspended*` | Decisión de seguridad; RNF-37 | Implementada localmente. |
| RN-USR-11 | Solo empresa o desarrollador autenticado puede editar su propio perfil y el cambio debe auditarse. | Cuenta activa; rol soportado. | Guarda campos permitidos y crea `LogAuditoria`; otro rol no edita. | `usuarios/views/profile_views.py::editar_perfil` | Pruebas de perfil en `test_dashboard.py` | RF 1.1.2, 1.2.2, 7.1.2 | Parcial: falta evidencia focalizada equivalente para todas las superficies empresariales. |
| RN-USR-12 | Un desarrollador verificado o en revisión no puede cambiar ficha, programa o estado desde el formulario de perfil. | Perfil `verificado` o `en_revision`. | Campos preservados incluso ante POST manipulado. | `PerfilDesarrolladorForm` | `test_perfil_form_bloquea_ficha_y_programa_si_verificado` | RF 9.1.1 | Implementada en formulario; no es constraint del modelo. |
| RN-USR-13 | La verificación empresarial es documental/humana y una empresa no verificada puede publicar con advertencia. | Empresa registrada. | Revisión administrativa y badge; publicación no equivale a verificación. | Flujos de verificación empresarial y badges | Pruebas de verificación/badges | RF 9.2.1 y 9.2.2; RF-N11 | Parcial: no existe integración demostrada con RUES/Cámara. |

## 4. Administración y auditoría

| ID | Regla normativa | Actor y precondición | Resultado o rechazo | Implementación autoritativa | Prueba relacionada | Origen | Estado y límite |
|---|---|---|---|---|---|---|---|
| RN-ADM-01 | El rol `administrador` determina `is_superuser` e `is_staff`; retirar el rol retira privilegios. | Alta o cambio de rol. | Administrador obtiene privilegios; otro rol no. | `Usuario.save`; `UsuarioQuerySet.update`; `Usuario.is_staff` | Pruebas de Django admin | RF 1.3.4; RNF-38 | Implementada para esos caminos; SQL y `bulk_update` pueden eludirla. |
| RN-ADM-02 | Paneles, APIs, reportes, historial y visor técnico exigen rol administrador. | Solicitud autenticada o anónima. | Acceso permitido al administrador; redirección o 403 para otros. | Vistas admin; `logs/views.py::_exigir_admin` | `usuarios/tests/test_admin.py`; `logs/tests/test_logs.py` | RF 1.3.1–1.3.3, 7.2.1–7.2.3 | Implementada; el tipo de rechazo no es uniforme entre rutas. |
| RN-ADM-03 | Desactivar o suspender invalida sesiones; reactivar limpia intentos y bloqueo. | Administrador; usuario objetivo. | Actualiza estado/is_active y elimina sesiones activas. | `admin_toggle_usuario`; APIs admin; `invalidar_sesiones_activas_usuario` | Pruebas admin de estado y sesión | RF 1.3.2 | Implementada localmente. |
| RN-ADM-04 | Una suspensión masiva no puede suspender al administrador ejecutor y genera auditoría por cada afectado. | Administrador; lista y acción válidas. | Auto-suspensión excluida; cada cambio conserva antes/después. | `usuarios/views/admin_api.py::api_bulk_toggle` | Pruebas bulk en `test_admin.py` | RF-N30; decisión de auditoría | Implementada localmente. |
| RN-ADM-05 | Crear, editar o eliminar usuarios por API exige administración, método correcto, validación y auditoría; no se permite autoeliminación. | Administrador. | Errores 400/405/409 según causa; éxito crea log. | `api_crear_usuario`; `api_actualizar_usuario`; `api_eliminar_usuario` | `test_admin.py`; `test_admin_api_cache.py` | RF 7.1.2 | Parcial: revisar dominio de rol y política de contraseña en creación administrativa. |
| RN-ADM-06 | APIs administrativas de mutación aplican límite por endpoint e identidad. | Consumidor de API. | Al superar 30 solicitudes/60 s: 429 con `Retry-After`. | `usuarios/decorators.py::api_ratelimit` | Pruebas de rate limit admin | RNF-22 | Implementada localmente; depende del backend de caché/proxy. |
| RN-ADM-07 | El log conserva actor opcional, acción, entidad, registro, valores anterior/nuevo y fecha. | Evento sensible. | Registra evento sin secretos ni contenido confidencial. | `logs/models.py::LogAuditoria`; instrumentación por dominio | Pruebas de logs y dominios | RF 7.1.2; decisión 3 | Parcial: cobertura se valida por recorrido; no captura universal de SQL/ORM. |
| RN-ADM-08 | Un log persistido no puede modificarse ni eliminarse por métodos de instancia. | Log existente. | `save()`/`delete()` lanzan error. | `LogAuditoria.save`, `delete` | `test_log_registrado_no_puede_modificarse_ni_eliminarse` | RNF-31 | Parcial: no es inmutabilidad de base de datos. |
| RN-ADM-09 | El historial filtra por usuario, entidad, acción y rango de fechas, más reciente primero. | Administrador. | Fecha inválida: 400; máximo 200 filas visibles. | `logs/views.py::historial_actividad` | Pruebas de historial | Capacidad interna M7 | Implementada; sin paginación posterior a 200. |
| RN-ADM-10 | Los reportes oficiales de aprendices, empresas y proyectos son exclusivos de administración. | Administrador. | Descarga CSV; no administrador bloqueado. | `logs/views.py::reporte_*_csv` | Pruebas de contenido/autorización | RF 7.2.1–7.2.3 | Implementada localmente; no constituye aceptación gerencial del formato. |

## 5. Proyectos y vacantes

| ID | Regla normativa | Actor y precondición | Resultado o rechazo | Implementación autoritativa | Prueba relacionada | Origen | Estado y límite |
|---|---|---|---|---|---|---|---|
| RN-PROY-01 | Solo una empresa autenticada puede publicar un proyecto con al menos una vacante y fecha de cumplimiento válida. | Empresa; formulario válido. | Crea en `publicado` y registra estado inicial; datos inválidos se rechazan. | `proyectos/views.py::crear_proyecto`; `Proyecto.vacantes` | `proyectos/tests/test_views.py::TestCrearProyecto` | RF 2.1.1–2.1.3 | Implementada principalmente en vista. |
| RN-PROY-02 | Una vacante está comprometida por contrataciones `activa`/`en_disputa` y postulaciones `en_negociacion`. | Proyecto existente. | Disponibles = máximo entre vacantes menos compromisos y cero. | `Proyecto.vacantes_disponibles` | Pruebas de modelos/cupos | RF 2.1.2, 3.3.2; RF-N08 | Implementada localmente. |
| RN-PROY-03 | Solo proyectos `publicado` o `en_desarrollo`, con cupo y plazo vigente, aceptan postulaciones. | Proyecto visible. | Sin cupo, vencido o en otro estado: bloqueo. | `Proyecto.acepta_postulaciones`; vista de postulación | Pruebas de postulación y modelo | Excepción aprobada a RF 3.1.1 | Implementada; existe una policy histórica más restrictiva que debe mantenerse alineada. |
| RN-PROY-04 | La empresa no puede reducir vacantes por debajo de contratos y negociaciones comprometidos. | Propietaria; proyecto editable. | Rechaza reducción y conserva valor anterior. | `proyectos/views.py::editar_proyecto` | Pruebas relacionadas de negociación/cupos | RF 2.2.2, 3.3.2 | Implementada en vista; falta servicio único. |
| RN-PROY-05 | La edición depende del estado y de compromisos existentes. | Empresa propietaria. | En trabajo: solo título/prioridad sin contrato activo; condiciones técnicas solo en publicado sin negociación ni contratos históricos; estados terminales/disputa no editan. | `editar_proyecto` | `TestEditarProyecto` | RF 2.2.2 | Implementada localmente; aceptación de producto pendiente. |
| RN-PROY-06 | El retiro directo solo aplica a un proyecto `publicado` sin contratos. | Empresa propietaria. | Pasa a retirado/inactivo; no cancela obligaciones contractuales. | `proyectos/views.py::desactivar_proyecto` | `TestDesactivarProyecto` | RF 2.2.3 con excepción documentada | Implementada localmente. |
| RN-PROY-07 | Solo la empresa propietaria puede finalizar desde `en_desarrollo` o `en_revision`, con al menos un hito y todos completos. | Propietaria; hitos completos. | Estado o hitos inválidos: rechazo. | `proyectos/policies.py`; `proyectos/services.py::validar_finalizacion` | `TestValidarFinalizacion`; `TestFinalizarProyecto` | RF 5.1.1 | Implementada localmente. |
| RN-PROY-08 | Finalizar cierra contrataciones activas, notifica y registra historial/auditoría. | RN-PROY-07 satisfecha. | Proyecto `finalizado`; contratos activos `finalizada`. | `proyectos/services.py::_finalizar_bloque` | `test_cierra_contratos_notifica_y_registra_historial` | RF 5.1.1 y 5.1.2 | Implementada localmente. |
| RN-PROY-09 | La finalización es irreversible; continuar crea un único sucesor directo vinculado. | Administrador; original finalizado y sin sucesor. | Nuevo proyecto; original, contratos, hitos, valoraciones e historial no cambian. | `Proyecto.proyecto_origen`; `admin_reactivar_proyecto` | `TestContinuacionProyectoFinalizado` | Decisión aprobada 1; RF-N04 | Implementada localmente; nombre de ruta heredado no implica reactivación. |

## 6. Postulaciones y negociación

| ID | Regla normativa | Actor y precondición | Resultado o rechazo | Implementación autoritativa | Prueba relacionada | Origen | Estado y límite |
|---|---|---|---|---|---|---|---|
| RN-POST-01 | Solo un desarrollador SENA verificado puede postularse a un proyecto elegible. | Desarrollador verificado; proyecto abierto. | Crea `pendiente`; otro rol, no verificado o proyecto no elegible: rechazo. | `postulaciones/views.py::postularse_a_proyecto` | `postulaciones/tests/test_postulaciones.py` | RF 3.2.1 y 9.1.1 | Implementada en vista; policy histórica no es la única autoridad. |
| RN-POST-02 | Solo se permite una postulación por desarrollador/proyecto y máximo tres procesos activos combinados. | Desarrollador verificado. | Duplicado o cuarto proceso: rechazo. | Constraint de `Postulacion`; vista de postulación | Pruebas de postulación | Decisión interna asociada a RF 3.2.1 | Implementada; revisar si contratos `en_disputa` deben contar en el límite personal. |
| RN-POST-03 | La carta es obligatoria; una postulación exitosa notifica a la empresa. | POST válido. | Persiste mensaje y crea notificación transaccional. | `postularse_a_proyecto` | `test_postularse_notifica_a_la_empresa` | RF 3.2.1 y 6.2.2 | Implementada localmente. |
| RN-POST-04 | La empresa selecciona entre dos y cuatro candidatos para comparación simultánea, sin ranking automático. | Empresa propietaria; candidaturas del proyecto. | 0–1 no habilita; 2–4 compara; quinto se bloquea. | `templates/postulaciones/lista_recibidas.html` | `tests/e2e/test_comparar_candidatos_ui.py` | Decisión aprobada 2; RF 3.2.2 | Parcial: límite cliente-side; falta evidencia actual de extremos 4/5 y aceptación visual. |
| RN-POST-05 | Aceptar una postulación inicia negociación y no crea contratación directa. | Empresa propietaria; postulación pendiente; cupo. | `en_negociacion`, reserva de cupo y contrato digital borrador. | URL heredada → `iniciar_negociacion`; bloqueo del servicio antiguo | Pruebas `TestAceptarPostulacion` | Excepción aprobada a RF 3.3.1; RF 8.1.2 | Implementada localmente. |
| RN-POST-06 | Solo la propietaria puede iniciar negociación, desde pendiente y con cupo. | POST; proyecto bloqueado. | Estado/cupo/actor inválido: no muta. | `postulaciones/views.py::iniciar_negociacion` | `TestIniciarNegociacion` | RF 3.3.2 y 8.1.2 | Implementada; concurrencia real requiere PostgreSQL. |
| RN-POST-07 | El plazo global es administrativo, entero de 1–30 días y predeterminado 7. | Administrador. | Actualiza singleton y audita; otro rol/rango inválido: rechazo. | `ConfiguracionNegociacion`; `actualizar_plazo_negociacion_dias` | `test_configuracion_negociacion.py` | Decisión aprobada 4 | Implementada localmente. |
| RN-POST-08 | Al iniciar se congela una fecha límite absoluta; cambios globales solo afectan negociaciones nuevas. | Negociación nueva. | Guarda `fecha_limite_negociacion`. | `iniciar_negociacion`; `Postulacion.fecha_limite_negociacion` | Prueba de plazo congelado | Decisión aprobada 4 | Implementada localmente. |
| RN-POST-09 | Una negociación vencida rechaza la postulación, expira contrato no firmado y libera reserva. | `en_negociacion`; fecha vencida. | Estados, avisos y auditoría; contrato firmado no expira. | `postulaciones/services.py::expirar_negociacion` | `test_expiracion_negociaciones.py` | RF-N07 | Parcial: servicio localizado; tarea Celery requiere reverificación. |
| RN-POST-10 | La empresa propietaria puede rechazar una postulación pendiente o en negociación. | Empresa propietaria. | Postulación y borrador no firmado quedan rechazados; notifica y audita. | `postulaciones/services.py::rechazar_postulacion` | `TestRechazarPostulacion` | RF interno 3.4.1 | Implementada localmente. |

## 7. Contrato digital y contratación

| ID | Regla normativa | Actor y precondición | Resultado o rechazo | Implementación autoritativa | Prueba relacionada | Origen | Estado y límite |
|---|---|---|---|---|---|---|---|
| RN-CON-01 | Cada postulación tiene como máximo un contrato digital; proyecto/desarrollador, una contratación. | Creación. | La base rechaza duplicados. | `ContratoDigital.postulacion`; constraint de `Contratacion` | `test_un_contrato_por_postulacion` | RF 8.2.1–8.3.1 | Implementada; falta prueba focalizada equivalente de toda unicidad de contratación. |
| RN-CON-02 | Solo la empresa parte edita términos antes de cualquier firma y durante negociación vigente. | Empresa; borrador/pendiente sin firmas. | Guarda términos y audita; otra parte/estado: rechazo. | `_contrato_editable`; `ver_contrato_digital` | `TestVerContratoDigital` | RF 8.2.1 | Parcial: verificar exposición de todas las cláusulas editables. |
| RN-CON-03 | Solo empresa y desarrollador partes firman, con aceptación expresa y negociación vigente. | Parte contractual; POST. | Falta de aceptación, tercero, doble firma, estado o plazo inválido: rechazo. | `firmar_contrato_digital`; `_permisos_firma` | `TestFirmarContratoDigital` | RF 8.2.2 | Implementada localmente. |
| RN-CON-04 | La primera firma congela contrato y evidencia profesional; alterar el contenido bloquea la segunda. | Primera firma válida. | Guarda snapshot y hash; estado `pendiente_firma`. | `ContratoDigital.calcular_hash_documento`; `obtener_perfil_profesional` | Pruebas de snapshot/hash | RF 8.2.2; RF-N06, RNF-23 | Implementada para nuevos contratos; legados no inventan evidencia. |
| RN-CON-05 | Una firma no contrata; solo ambas firmas formalizan. | Contrato vigente. | Segunda firma: contrato firmado, postulación aceptada, contratación activa, equipo y transición del proyecto. | `activar_contratacion_formal`; `firmar_contrato_digital` | Pruebas de primera/segunda firma | RF 8.2.2 y 8.3.1 | Implementada localmente. |
| RN-CON-06 | Incluso con doble firma, no se formaliza si el cupo se agotó. | Ambas firmas; proyecto bloqueado. | Rechazo atómico sin contratación extra. | `activar_contratacion_formal` | `test_formalizar_contrato_digital_bloquea_si_cupo_se_agoto` | RF 3.3.2; RF-N08 | Implementada; concurrencia real requiere PostgreSQL. |
| RN-CON-07 | Al llenarse cupos se rechazan y notifican las postulaciones pendientes restantes. | Contratación llena último cupo. | Pendientes → rechazadas con aviso. | `activar_contratacion_formal` | Prueba de rechazo por cupo | RF 8.3.1 | Parcial: otras negociaciones abiertas no se rechazan automáticamente. |

## 8. Hitos y avances

| ID | Regla normativa | Actor y precondición | Resultado o rechazo | Implementación autoritativa | Prueba relacionada | Origen | Estado y límite |
|---|---|---|---|---|---|---|---|
| RN-AVA-01 | La empresa crea hitos y equipos con miembros contratados en su proyecto. | Empresa propietaria. | Hito/equipo queda asociado; miembro ajeno o sin contrato activo: rechazo. | `proyectos/views.py::gestionar_hitos`, `gestionar_equipos` | `proyectos/tests/test_views.py` | RF 4.1.1 y 4.1.2 | Implementada localmente. |
| RN-AVA-02 | Solo un desarrollador con contratación activa registra avances en proyecto de trabajo. | Contratado; proyecto `en_desarrollo`/`en_revision`. | Sin contrato, estado o hito disponible: no crea avance. | `avances/views.py::registrar_avance` | `avances/tests/test_avances.py` | RF 4.2.1 | Implementada; concurrencia real requiere reverificación. |
| RN-AVA-03 | Solo puede avanzar un hito propio, de su equipo o general. | Contrato activo; hito pendiente. | Hito ajeno: rechazo. | `registrar_avance` | Pruebas de asignación individual/equipo | RF 4.1.2 y 4.2.1; RF-N01, N02 | Implementada en vista. |
| RN-AVA-04 | La descripción es obligatoria y suficiente; URL y archivo son opcionales. | Desarrollador autorizado. | Descripción vacía o archivo/URL inválidos: rechazo. | `registrar_avance`; `_validar_archivo_adjunto` | Pruebas de evidencia en `test_avances.py` | RF 4.2.1 | Implementada; privacidad de adjuntos de avances no demostrada. |
| RN-AVA-05 | Registrar avance marca hito `en_revision`; si no quedan pendientes, proyecto `en_revision`; GET no muta. | Avance válido. | Crea avance pendiente, notifica y registra transición. | `registrar_avance` | Pruebas de registro y GET sin mutación | RF 4.2.2 y 4.3.4; RNF-35 | Implementada localmente. |
| RN-AVA-06 | Solo la empresa propietaria revisa una vez un avance pendiente en proyecto revisable. | Empresa dueña. | Actor/estado inválido o revisión repetida: rechazo. | `avances/views.py::revisar_avance` | `TestRevisarAvance` | RF 4.3.1 y 4.3.2 | Implementada con transacción/lock; no prueba integral de concurrencia. |
| RN-AVA-07 | Aceptar completa hito; aceptar el último finaliza el proyecto antes de las valoraciones. | Revisión válida. | Avance aceptado, hito completado y cierre si corresponde. | `revisar_avance`; `finalizar_proyecto` | `test_empresa_acepta_avance_pendiente_exitosamente` | RF 4.3.1 y 5.1.1 | Implementada localmente. |
| RN-AVA-08 | Rechazar exige comentario, devuelve hito a pendiente y proyecto a desarrollo. | Revisión válida. | Sin comentario: rechazo; con comentario: transición y aviso. | `revisar_avance`; `Entregable.save` | Prueba de rechazo con comentario | RF 4.3.2 y 4.3.3 | Implementada; longitud/calidad no prueba mérito sustantivo. |

## 9. Cancelación, disputas y evidencia

| ID | Regla normativa | Actor y precondición | Resultado o rechazo | Implementación autoritativa | Prueba relacionada | Origen | Estado y límite |
|---|---|---|---|---|---|---|---|
| RN-DIS-01 | La ruta histórica de cancelación crea una solicitud; nunca cancela unilateralmente. | Parte de contrato activo; sin disputa/solicitud viva. | Contrato y cupo permanecen hasta decisión. | `cancelar_contratacion`; `solicitar_cancelacion` | Pruebas de solicitud/cupo | RF 3.4.1; RF-N09 | Implementada; longitud mínima no prueba causal. |
| RN-DIS-02 | Acuerdo mutuo requiere confirmación de la contraparte. | Solicitud pendiente; decide quien no la creó. | Aprobación cancela; rechazo/silencio conserva contrato y cupo. | `resolver_solicitud_cancelacion` | Pruebas bilaterales | Decisión aprobada 7 | Implementada; sin sanción automática. |
| RN-DIS-03 | Incumplimiento e inactividad se tramitan por disputa y requieren evidencia. | Parte contractual. | Cancelación ordinaria rechazada; sin evidencia no congela. | Servicios de cancelación y disputa | Pruebas integradas | Decisiones 6 y 7 | Implementada localmente. |
| RN-DIS-04 | Fuerza mayor empieza como propuesta bilateral; al escalar exige evidencia o declaración justificada de indisponibilidad. | Parte contractual. | Sin soporte/declaración: no abre mediación. | `solicitar_cancelacion`; `abrir_disputa` | Pruebas de fuerza mayor | Decisiones 6 y 7 | Implementada; rechazo bilateral no abre disputa automáticamente. |
| RN-DIS-05 | Solo partes vinculadas abren disputa con contrato activo y proyecto en trabajo. | Empresa/desarrollador parte; relato y confirmaciones. | Apertura atómica congela proyecto/contrato; tercero/estado/relato inválido: rechazo. | `disputas/services.py::abrir_disputa` | Pruebas de apertura/congelamiento | RF 10.1.1 | Implementada; 80 caracteres no prueban veracidad. |
| RN-DIS-06 | Evidencia es obligatoria para incumplimiento, inactividad, falta grave de comunicación y bloqueo de insumos. | Apertura por causal. | Sin URL/archivo: no congela. | `CATEGORIAS_EVIDENCIA_OBLIGATORIA`; `abrir_disputa` | Prueba de incumplimiento sin evidencia | Decisión aprobada 6 | Implementada; evidencia no determina sanción. |
| RN-DIS-07 | Evidencia admite URL, PDF, ZIP, PNG, JPG/JPEG y archivo máximo 10 MB. | Apertura de disputa. | Formato/tamaño inválido: rechazo. | `disputas/validators.py` | Pruebas de evidencia | Decisión aprobada 6 | Implementada localmente. |
| RN-DIS-08 | Archivos de disputa son privados para partes y administración. | Usuario autenticado. | Tercero denegado; descarga por ruta autorizada. | `descargar_evidencia_view`; configuración Nginx | Prueba de descarga privada | Decisión aprobada 6 | Parcial: verificar almacenamiento/proxy en despliegue. |
| RN-DIS-09 | Abrir disputa conserva el cupo y desplaza una solicitud pendiente sin borrar historial. | Disputa válida. | Contrato `en_disputa`; solicitud previa queda rechazada/referenciada. | `abrir_disputa` | Pruebas de cupo e historial | RF 10.1.1; decisión 7 | Implementada localmente. |
| RN-DIS-10 | Solo administración resuelve una vez, con acción válida y dictamen no vacío. | Disputa abierta/en mediación. | Actor/acción/dictamen/estado inválido: rechazo. | `resolver_disputa`; vista de resolución | Pruebas de resolución | RF 10.2.1 y 10.2.2 | Implementada; no equivale a validación jurídica. |
| RN-DIS-11 | Cuatro acciones se agrupan en continuidad, terminación y sanción. | Disputa resuelta. | Reanudar→continuidad; cancelar→terminación; sanciones→sanción. | `Disputa.FAMILIA_POR_RESOLUCION`; `familia_resolucion` | Prueba parametrizada de familias | Decisión aprobada 5 | Implementada; familia no reemplaza acción. |
| RN-DIS-12 | La resolución aplica efectos atómicos y notifica. | Dictamen válido. | Reanudar, cancelar o sancionar modifica proyecto/contrato/usuario según acción. | `resolver_disputa` | Pruebas de cuatro resoluciones | RF 10.3.1; RF-N16 | Parcial: sin aceptación automática de avances ni ajuste automático de calificaciones. |
| RN-DIS-13 | Cancelar o sancionar al desarrollador rechaza avances pendientes y devuelve hitos en revisión; reanudar los conserva. | Resolución vinculada a desarrollador. | Limpieza consistente sin alterar avances aceptados. | `resolver_disputa` | Pruebas de efectos sobre avances/hitos | RF 10.3.1 | Implementada localmente. |

## 10. Finalización, valoraciones y reputación

| ID | Regla normativa | Actor y precondición | Resultado o rechazo | Implementación autoritativa | Prueba relacionada | Origen | Estado y límite |
|---|---|---|---|---|---|---|---|
| RN-VAL-01 | Las valoraciones ocurren después del cierre y hasta 30 días después de una fecha fiable. | Parte participante; proyecto finalizado. | Antes del cierre, fuera del plazo o sin fecha fiable: rechazo. | `validar_plazo_valoracion`; vistas de valoración | Pruebas de ventana | RF 5.2.1–5.3.3 | Implementada localmente. |
| RN-VAL-02 | Empresa valora a cada desarrollador; desarrollador valora a empresa, con 1–5 y comentario mínimo de 20 caracteres. | Participante; dentro de ventana. | Puntuación/comentario inválido: rechazo. | `valorar_y_finalizar_si_ultima`; `calificar_empresa` | Pruebas de valoración | RF 5.2.1 y 5.2.2 | Implementada; longitud no valida calidad/veracidad. |
| RN-VAL-03 | Solo existe una valoración por proyecto, desarrollador y rol; publicada es inmutable por aplicación. | Primera valoración válida. | Duplicado o edición: rechazo. | Constraint de `Valoracion`; `Valoracion.save` | Pruebas de duplicado/inmutabilidad | RF 5.3.3 | Implementada por ORM/constraint; SQL directo queda fuera. |
| RN-VAL-04 | La valoración recalcula el promedio simple denormalizado de la contraparte por cohorte. | Nueva valoración. | Empresa→dev; desarrollador→empresa. | `recalcular_reputacion_desarrollador/empresa` | Pruebas de promedio | RF 5.3.1 | Implementada; no es reputación bayesiana. |
| RN-VAL-05 | Reputación bayesiana = `(v/(v+m))×R + (m/(v+m))×C`, con dos decimales y cohortes separadas. | Valoraciones recibidas. | Con cero valoraciones muestra `C` como referencia, no mérito. | `calcular_reputacion_bayesiana`; métricas de desarrollador | Pruebas bayesianas | Decisión aprobada 8; RF-N31 | Parcial: agregador explícito localizado solo para desarrolladores y UI no alineada completamente. |
| RN-VAL-06 | `m` inicia en 5, admite 1–100 y solo administración lo cambia con auditoría. | Administrador. | Otro rol/rango inválido: rechazo. | `ConfiguracionReputacion`; servicio de actualización | Pruebas de configuración | Decisión aprobada 8 | Implementada localmente. |
| RN-VAL-07 | Un cierre histórico sin fecha fiable requiere regularización con fecha real, actor, motivo y evidencia de referencia. | Administrador; proyecto finalizado legado. | Sin regularización no se abre ventana; fecha inválida no muta ni reinicia una ventana vencida. | `regularizar_cierre_historico`; `obtener_fecha_cierre_fiable` | `test_valoraciones_historicas.py` | Decisión de preservación histórica | Implementada localmente; no sustituye evidencia externa. |

## 11. Mensajería y notificaciones

| ID | Regla normativa | Actor y precondición | Resultado o rechazo | Implementación autoritativa | Prueba relacionada | Origen | Estado y límite |
|---|---|---|---|---|---|---|---|
| RN-MSG-01 | El chat directo requiere relación válida; no se permite autochat. | Usuarios autenticados relacionados. | Sin relación o mismo usuario: `PermissionDenied`. | `mensajes/policies.py::puede_comunicarse` | `mensajes/tests/test_services.py` | RF 6.1.1 y 6.1.2 | Implementada; política no comprueba por sí sola estado activo. |
| RN-MSG-02 | El mensaje debe tener contenido no vacío y máximo 2.000 caracteres. | Remitente autorizado. | Vacío/exceso: rechazo. | `mensajes/services.py::_validar_contenido` | Pruebas de contenido | Regla interna M6 | Implementada en servicio; sin constraint equivalente en modelo. |
| RN-MSG-03 | Proyecto finalizado conserva historial pero queda en solo lectura. | Participante de proyecto finalizado. | Nuevo mensaje directo/grupal: rechazo. | `_validar_proyecto_activo` | Pruebas de proyecto finalizado | RF 6.1.1–6.1.3 | Implementada localmente. |
| RN-MSG-04 | Crear mensaje directo y notificación interna es atómico. | Envío válido. | Ambos se crean o ninguno. | `mensajes/services.py::enviar_mensaje` | `test_crea_mensaje_y_notificacion` | RF 6.2.1 | Implementada; no prueba correo/push. |
| RN-MSG-05 | Chat grupal admite empresa propietaria, contratados y administración; ajenos se rechazan. | Participante del proyecto. | Mensaje y avisos al equipo salvo remitente. | `puede_participar_en_chat_grupal`; `enviar_mensaje_grupal` | Pruebas grupales | Extensión RF-N20 | Implementada localmente. |
| RN-MSG-06 | WebSocket exige autenticación/autorización y aísla salas. | Conexión WebSocket. | Anónimo 4401; sin permiso 4403. | Consumers de mensajería | Pruebas de consumers | RF-N20; RNF-25, 29 | Parcial: sin prueba de carga/reconexión/Redis desplegado. |
| RN-MSG-07 | Solo remitente/receptor ve un mensaje directo; el receptor puede marcarlo leído. | Parte del mensaje. | Tercero no accede; apertura/recepción marca lectura. | `puede_ver_mensaje`; vistas/consumer | Pruebas de chat directo | RF 6.1.3 | Implementada localmente. |
| RN-MSG-08 | Auditoría administrativa de conversaciones exige rol admin y audita la consulta. | Administrador. | Filtros/paginación; no admin bloqueado. | `admin_auditar_mensajes` | `test_auditoria_chats.py` | RF-N26 | Implementada; acceso expone contenido completo y requiere control operativo. |
| RN-NOT-01 | Listar, leer y limpiar notificaciones opera solo sobre el destinatario; mutaciones requieren POST. | Usuario autenticado. | No altera notificaciones ajenas. | `notificaciones/views.py` | `test_notificaciones.py` | RF 6.2.1–6.2.3 | Implementada localmente. |
| RN-NOT-02 | Notificación nueva nace no leída y puede vincularse a proyecto. | Evento de negocio. | Persiste para destinatario. | `Notificacion` | Pruebas del modelo | RF 6.2.* | Implementada; texto sin límite explícito. |
| RN-NOT-03 | SSE entrega conteo y nuevas notificaciones por usuario autenticado. | Sesión válida. | Emite sincronización/heartbeat. | `notificaciones_stream`; generador SSE | `notificaciones/tests/test_sse.py` | RF-N19; RNF-29, 36 | Parcial: sondeo local; proxy/capacidad desplegada no verificados. |
| RN-NOT-04 | El correo transaccional es asíncrono y un fallo al encolar no revierte el negocio persistido. | Evento que solicita correo. | Reintenta; si broker falla, devuelve falso. | `despachar_email_transaccional`; tarea Celery | `notificaciones/tests/test_tasks.py` | RNF-28 | Parcial: encolar no prueba entrega. |
| RN-NOT-05 | Avisos de cumplimiento se deduplican y una reprogramación retira avisos obsoletos no leídos. | Fecha de cumplimiento. | Empresa/admin activos reciben alerta anticipada/vencida una vez. | `enviar_avisos_cumplimiento_task`; `AvisoCumplimiento` | `test_avisos_cumplimiento.py` | RF 2.1.3 | Parcial: Beat/worker en despliegue no verificados. |
| RN-NOT-06 | La depuración automática elimina notificaciones leídas antiguas; no leídas se conservan salvo opción explícita. | Tarea/administrador. | Purga conforme a edad/configuración. | `depurar_notificaciones`; Beat | Pruebas de cleanup | RF-N25 | Parcial: Beat usa 30 días y comando 90; política debe unificarse. |

## 12. Archivos, favoritos y operación

| ID | Regla normativa | Actor y precondición | Resultado o rechazo | Implementación autoritativa | Prueba relacionada | Origen | Estado y límite |
|---|---|---|---|---|---|---|---|
| RN-ARC-01 | Adjuntos de avances admiten PDF/ZIP/PNG/JPG hasta 10 MB y validan firma/estructura. | Desarrollador autorizado. | Archivo inválido: no crea avance. | `_validar_archivo_adjunto` | Pruebas de magic bytes/extensión | RNF-13 | Implementada en vista; creación ORM puede omitirla. |
| RN-ARC-02 | Documentos de verificación solo son descargables por titular o administración. | Titular/admin. | URL temporal R2 o `FileResponse`; tercero bloqueado. | Vistas de verificación; `services_storage.py` | `test_services_storage.py` y vistas | RF-N13, N14; RNF-34 | Parcial: R2 real no verificado. |
| RN-ARC-03 | URLs R2 usan nombre saneado, UUID y expiración limitada. | Usuario autenticado; tipo permitido. | Subida 300 s y descarga 900 s por defecto; fallo retorna `None`. | `generar_url_*_prefirmada` | Pruebas con mocks | RNF-34 | Parcial: falta validar proveedor real y asociación E2E del objeto. |
| RN-ARC-04 | Evidencias de disputa y verificaciones no se sirven por ruta pública directa. | Solicitud de archivo. | Nginx bloquea acceso directo; aplicación autoriza. | `docker/nginx/nginx.conf`; vistas protegidas | Pruebas de vista | Decisión 6; RF-N13 | Parcial: configuración operativa no verificada. |
| RN-ARC-05 | Los adjuntos de avances permanecen bajo `/media/` público en la configuración de referencia. | Conocimiento de URL. | Nginx puede servirlos sin autorización de la vista. | Configuración Nginx | Sin prueba específica | Privacidad/retención | Brecha: definir y aplicar política de privacidad para evidencia de avances. |
| RN-FAV-01 | Solo desarrolladores pueden gestionar favoritos. | Usuario autenticado. | Otro rol: 403 o redirección. | `favoritos/views.py` | `favoritos/tests/test_favoritos.py` | RF-N23 | Implementada en vista; no constraint DB de rol. |
| RN-FAV-02 | Solo se agrega un proyecto publicado; se puede retirar aunque luego cambie de estado. | Desarrollador. | Toggle agrega/retira. | `toggle_favorito` | Pruebas toggle | RF-N23 | Implementada; toggle repetido puede revertir intención. |
| RN-FAV-03 | Solo existe un favorito por desarrollador/proyecto. | Creación. | Duplicado bloqueado por constraint/manejo de carrera. | `Favorito.Meta` | Pruebas de unicidad/carrera simulada | RF-N23 | Implementada; sin prueba concurrente real. |
| RN-OPS-01 | Respaldo genera dump, verifica restaurabilidad, calcula SHA-256 y registra éxito/fallo. | Operador/tarea. | Resultado auditable con tamaño y ejecutor. | `backup_db` | `logs/tests/test_backup_commands.py` | RNF-14; RF-N28 | Parcial: `--skip-integrity-check` puede omitir verificación y volumen es local. |
| RN-OPS-02 | Retención de respaldos conserva diarios 7 días, uno semanal hasta 30 y purga lo anterior. | Respaldo programado. | Elimina archivo y checksum vencidos. | `logs/backups.py::plan_retention` | `logs/tests/test_backups.py` | RNF-14 | Implementada localmente; sin retención mensual/anual/off-site. |
| RN-OPS-03 | Ensayo de recuperación usa base temporal y objetivo predeterminado de 300 segundos. | Operador. | Restaura/reconstruye, verifica tablas y limpia; exceder objetivo falla. | `verify_db_recovery` | Pruebas de recuperación | RNF-14 | Parcial: ejecución bajo demanda; PostgreSQL/producción y media no verificados. |
| RN-OPS-04 | Notificaciones tienen depuración; mensajes, auditoría, favoritos y archivos no tienen retención implementada. | Operación. | No existe purga automática para esas clases. | Ausencia contrastada con servicios existentes | No aplica | Matriz de acceso/retención | Brecha: aprobar plazos y mecanismos antes de producción. |

## 13. Brechas y decisiones pendientes

| ID | Brecha o decisión | Cierre requerido |
|---|---|---|
| BR-RN-01 | Ficha y programa SENA siguen opcionales en registro, pese a formulaciones externas que pueden interpretarlos como obligatorios. | Decisión explícita del responsable del producto y actualización del formulario/matriz oficial de excepciones. |
| BR-RN-02 | La reputación bayesiana no está integrada uniformemente para empresas, rankings, reportes y todas las vistas. | Implementación y pruebas por superficie; no cambiar el promedio simple silenciosamente. |
| BR-RN-03 | Adjuntos de avances se sirven desde media pública. | Clasificación de privacidad, migración de almacenamiento y descarga autorizada. |
| BR-RN-04 | Retención de mensajes, auditoría, favoritos y archivos no está aprobada/implementada. | Política jurídica/operativa y tareas verificables de conservación/eliminación. |
| BR-RN-05 | Depuración de notificaciones tiene defaults distintos: 30 días en Beat y 90 en comando/servicio. | Unificar política y configuración. |
| BR-RN-06 | No existe consulta demostrada a RUES/Cámara para verificar empresas. | Aprobar proveedor, contrato técnico y política de fallo/degradación. |
| BR-RN-07 | Ajuste automático de calificaciones y aceptación automática de avances después de disputa no tienen regla aprobada. | Decisión de producto antes de implementar RF 10.3.1 literalmente. |
| BR-RN-08 | Algunas reglas viven en vistas y existen policies históricas no usadas o divergentes. | Consolidar autoridad en services/policies sin cambiar comportamiento aprobado. |
| BR-RN-09 | Locks/concurrencia críticos requieren pruebas reales en PostgreSQL. | Ejecutar pruebas de carrera en base descartable PostgreSQL. |
| BR-RN-10 | Celery, SSE, WebSocket, Redis, R2, correo y proxy tienen evidencia local/parcial, no despliegue verificado. | Verificación integrada en entorno equivalente a producción. |

## 14. Reglas de mantenimiento

1. Toda regla nueva debe recibir un ID estable y no reutilizable.
2. Una modificación de política debe actualizar esta matriz, la conciliación, la trazabilidad y los casos de prueba.
3. Una decisión aprobada no se marca como implementada sin ubicar código y prueba relacionada.
4. Una prueba relacionada no se marca como aceptación del producto ni evidencia de producción.
5. Los nombres heredados de rutas o funciones no cambian el significado normativo de la regla aprobada.
6. Las reglas de permisos deben verificarse por actor, objeto y estado, no solo por rol.
7. Las transiciones deben documentar estado inicial, estado final, efectos secundarios y rollback.
8. Los controles de archivos deben distinguir validación, autorización de descarga, almacenamiento y retención.
9. Los cambios de esquema deben actualizar migraciones y diagramas desde sus fuentes editables.
10. Cada revisión debe registrar checkout, entorno, comandos y límites en [Estado de verificación actual](ESTADO_VERIFICACION_ACTUAL.md).
