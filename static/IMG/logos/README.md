# Logos de empresas — carrusel de la landing (`#empresas`)

Este directorio es el punto de entrada para los logos del carrusel
"Empresas que confían en nosotros" de `templates/publico/index.html`.

## Reglas de uso

Solo se publican logos de empresas que sean **clientes reales** y que hayan
**autorizado el uso de su marca** por escrito (correo o cláusula contractual).
El carrusel es un claim de respaldo: usar marcas de terceros sin permiso es
falso endorsement y uso indebido de marca.

Registrá cada autorización en la tabla de abajo antes de agregar el archivo.

## Especificación técnica

- Nombre: `<slug>.svg` en minúsculas, sin espacios (ej. `grupo-andino.svg`).
- Formato preferido: **SVG** con `viewBox`, sin `width`/`height` fijos y con un
  único `fill` (ideal `currentColor`).
- Alternativa: **PNG con transparencia**, alto mínimo 96 px (ideal 240 px, 2x).
- Versión **monocroma clara** (blanco o gris `#c9c9c9`): el carrusel los pinta
  al 42 % de opacidad sobre fondo `#050505`. Un logo oscuro desaparece.
- Peso máximo: SVG < 15 KB, PNG < 80 KB.
- Sin fondo, sin sombras, sin caja contenedora.
- `alt` obligatorio con la razón social o nombre comercial.

## Registro de autorizaciones

| Empresa | Archivo | Fuente | Autorización (fecha / soporte) |
| --- | --- | --- | --- |
| _pendiente_ | | | |

## Estado actual

El carrusel muestra wordmarks de texto derivados de los casos de éxito del
sitio (`FINTECH COLOMBIA`, `ECOMMERCE NACIONAL`, …). Se reemplazan por
`<img>` a medida que existan archivos autorizados en este directorio.
