# Decisiones de producto aprobadas

## Propósito y alcance

Este documento consolida las ocho decisiones aprobadas por el responsable del producto para cerrar contradicciones entre la fuente oficial, el inventario interno y el comportamiento esperado de JobDevs.

La fuente oficial permanece intacta: `Matriz_de_Requisitos_JobDevs_VERIFICADA.xlsx`. Cuando una decisión difiere de su literalidad, se registra como excepción de producto y no como cumplimiento literal. «Aprobada» significa que la política ya fue decidida; no significa por sí sola que toda la implementación, aceptación visual o verificación de despliegue esté terminada.

## 1. Finalización irreversible y proyecto sucesor

- Un proyecto `finalizado` no puede volver a un estado de trabajo.
- Continuar el trabajo crea un proyecto nuevo vinculado mediante `Proyecto.proyecto_origen`.
- El original conserva cierre, hitos, contratos, valoraciones e historial.
- Los contratos del original no se reactivan.
- La acción administrativa heredada conserva su ruta por compatibilidad, pero su efecto es crear el sucesor.

Estado local: implementado en `proyectos/models.py`, `usuarios/views/admin_dashboard.py` y la migración `proyectos/0022_proyecto_proyecto_origen.py`; prueba focalizada en `usuarios/tests/test_admin.py::TestContinuacionProyectoFinalizado`.

## 2. Comparación de candidatos

- La empresa selecciona entre dos y cuatro candidatos.
- La comparación es simultánea y lado a lado, con criterios homogéneos.
- Debe incluir como mínimo verificación, programa/ficha SENA, habilidades, experiencia o evidencia profesional disponible, reputación, cantidad de valoraciones, proyectos completados, carta, perfil y estado de postulación.
- No existe puntuación automática ni recomendación de «mejor candidato».
- Una selección de cero o uno no habilita la comparación; no se permite un quinto candidato.

Estado local: interfaz implementada en `templates/postulaciones/lista_recibidas.html`; recorrido focalizado en `tests/e2e/test_comparar_candidatos_ui.py` aprobado después del cambio.

## 3. Auditoría de cambios sensibles

La auditoría obligatoria cubre cambios sensibles, no todas las escrituras indiscriminadamente.

Dominios incluidos:

- identidad, email, documento, rol, activación, suspensión y verificaciones;
- fichas y excepciones SENA;
- estado, vacantes y fechas de proyectos;
- postulaciones, negociaciones, contratos, firmas y cancelaciones;
- disputas, dictámenes y sanciones;
- valoraciones y regularizaciones históricas;
- configuración administrativa y de seguridad.

Cada evento debe conservar, cuando aplique: actor, fecha, entidad, identificador, acción, valor anterior y valor nuevo. Nunca debe copiar contraseñas, tokens, códigos, documentos completos ni contenido confidencial de chats o mediaciones.

Estado local: existen recorridos auditados en los dominios anteriores; se reforzaron altas, cambios, bajas y cambios masivos de cuentas. La garantía exhaustiva debe evaluarse por recorrido sensible; no se afirma captura universal de SQL directo o de cualquier `QuerySet.update()` administrativo.

## 4. Plazo global de negociación

- Valor predeterminado: siete días.
- Rango permitido: uno a treinta días.
- Solo administración puede modificarlo.
- El valor se copia al iniciar una negociación y queda congelado como fecha límite de esa negociación.
- Cambiar la configuración afecta únicamente negociaciones nuevas.
- El cambio debe quedar auditado con valor anterior y nuevo.

Estado local: implementado mediante `ConfiguracionNegociacion`, `postulaciones/migrations/0008_configuracionnegociacion.py`, servicio transaccional y control del panel administrativo. Las pruebas focalizadas de configuración e inicio de negociación aprobaron; falta registrar una regresión global posterior a todos los cambios.

## 5. Familias oficiales de resolución de disputas

Se conservan las cuatro acciones locales y se agrupan así:

| Acción local | Familia oficial |
|---|---|
| `reanudar_proyecto` | continuidad |
| `cancelar_contrato` | terminación |
| `sancionar_empresa` | sanción |
| `sancionar_desarrollador` | sanción |

La familia clasifica el resultado; no sustituye la acción concreta ni duplica una sanción como terminación. Los efectos siguen siendo transaccionales y requieren dictamen administrativo.

Estado local: mapeo expuesto por `Disputa.familia_resolucion` y cubierto por prueba parametrizada.

## 6. Política de evidencia

- Incumplimiento e inactividad: evidencia obligatoria.
- Fuerza mayor escalada a mediación: evidencia o declaración explícita y justificada de indisponibilidad.
- Acuerdo mutuo: no exige evidencia adicional; la confirmación inequívoca de la contraparte constituye la prueba del acuerdo.
- Formatos iniciales: URL, PDF, PNG, JPG o ZIP.
- Tamaño máximo de archivo: 10 MB.
- Los archivos son privados para las partes del contrato y administradores; se descargan por una ruta autorizada, no por una URL pública directa.
- Aportar o no aportar evidencia no genera sanciones automáticas.

Estado local: reglas, archivo privado, validación de formato/tamaño, declaración de indisponibilidad y descarga autorizada incorporados en `disputas`; migraciones `0005`–`0007`. Falta una regresión global posterior a este lote.

## 7. Cancelación sustantivamente justificada

- La longitud del texto no demuestra por sí sola una causa válida.
- Acuerdo mutuo requiere confirmación de contraparte.
- Fuerza mayor bilateral puede aportar evidencia; sin acuerdo pasa a mediación.
- Incumplimiento e inactividad se tramitan por disputa con evidencia.
- Contrato y vacante permanecen activos o congelados hasta una decisión definitiva.
- Solo una resolución expresa produce efectos y, cuando corresponda, sanción.
- El administrador debe fundamentar el dictamen; no existen sanciones automáticas por categoría, evidencia o silencio.

Estado local: el flujo bilateral y la mediación ya existían; la política de evidencia refuerza la evaluación sustantiva. El mínimo de caracteres permanece como requisito de calidad narrativa, no como prueba suficiente.

## 8. Reputación bayesiana transparente

Para cada tipo de destinatario se usan:

- `R`: promedio simple real de sus valoraciones;
- `v`: cantidad de valoraciones recibidas;
- `C`: promedio global de la misma cohorte;
- `m`: mínimo de confianza configurable, inicialmente 5.

Fórmula:

`(v / (v + m)) × R + (m / (v + m)) × C`

Reglas de presentación:

- mostrar por separado reputación bayesiana, promedio simple y cantidad;
- explicar los valores `R`, `v`, `C` y `m` usados;
- con cero valoraciones, presentar `C` como referencia inicial de la plataforma, no como mérito personal;
- calcular `C` por cohorte: valoraciones recibidas por desarrolladores y por empresas no se mezclan;
- cambios de `m` son administrativos y auditados.

Estado local: calculador con `Decimal`, configuración `m=5`, auditoría y métricas para desarrolladores están incorporados en `proyectos/services.py` y `proyectos/migrations/0023_configuracionreputacion.py`. La sustitución consistente de promedios simples en todas las interfaces, rankings y reportes todavía está pendiente; por tanto, esta decisión no debe marcarse como completamente implementada.

## Evidencia y límites

- No se ha autorizado commit, push, despliegue ni migración sobre una base de operación.
- Las pruebas focalizadas citadas son evidencia local, no aceptación del responsable del producto ni validación en producción.
- El último cierre global documentado es anterior a parte de estas implementaciones; debe repetirse antes de declarar cierre técnico de este paquete.
- Los diagramas y manuales derivados deben actualizarse desde sus fuentes editables y regenerarse; no se debe editar únicamente el PDF/PNG/SVG derivado.
