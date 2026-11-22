# Diagramas de secuencia — JobDevs

## Alcance

Estos diagramas detallan los intercambios entre actores, interfaz, vistas/servicios, persistencia y avisos en cinco flujos críticos. Complementan el [mapa de navegación](MAPA_NAVEGACION.md): el mapa indica pantallas y recorridos; las secuencias explican validaciones, transacciones y efectos secundarios.

Fuente visual editable: [`SECUENCIAS_JOBDEVS.drawio`](SECUENCIAS_JOBDEVS.drawio). PDF, PNG y SVG son derivados. Se regenera con `scripts/generate_sequence_diagrams.py`.

## Inventario

| Página | Flujo | Garantía representada |
|---|---|---|
| 01 | Negociación y doble firma | La primera firma no activa; la segunda firma activa atómicamente. |
| 02 | Registro y revisión de avance | Descripción obligatoria, evidencia opcional, revisión y cierre al último hito. |
| 03 | Cancelación y mediación | Solicitud no equivale a cancelación; mediación congela y el dictamen decide. |
| 04 | Cierre y sucesor | El cierre es irreversible y la continuidad crea un proyecto nuevo vinculado. |
| 05 | Verificación | Solicitud, documento autorizado, decisión administrativa y aviso al titular. |

## Fuentes de implementación contrastadas

- `postulaciones/views.py::iniciar_negociacion`: bloqueo de proyecto/postulación, capacidad, plazo, contrato, notificaciones y auditoría.
- `contrataciones/views.py::firmar_contrato_digital` y `activar_contratacion_formal`: firmas, hash/snapshot y activación con ambas partes.
- `avances/views.py::registrar_avance` y `revisar_avance`: autorización del contratado, validación de evidencia, revisión, notificación y cierre al último hito.
- `contrataciones/services.py` y `contrataciones/views.py`: solicitud y resolución de cancelación.
- `disputas/views.py` y `disputas/services.py`: apertura, evidencia autorizada, mediación y resolución.
- `proyectos/services.py::finalizar_proyecto`: finalización y valoraciones posteriores.
- `usuarios/urls.py` y vistas de verificación: solicitud, revisión administrativa y documentos de soporte.

## Límites

- Las flechas describen comportamiento local contrastado contra código; no acreditan despliegue ni aceptación de producto.
- Las notificaciones se representan como efecto de dominio; su entrega en tiempo real depende de infraestructura que se verifica por separado.
- La verificación documental no se presenta como consulta real a RUES/Cámara ni sincronización externa SENA.
- Las ramas de rechazo y error se resumen en notas cuando no cambian el orden principal del flujo.

## Mantenimiento

Cuando una regla cambie, actualizar el diagrama del flujo afectado, este documento, la matriz de reglas, trazabilidad y casos de prueba. Para un flujo nuevo, no dibujar una integración externa como realizada sin una ruta, servicio o evidencia verificable.
