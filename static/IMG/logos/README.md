# Logos de empresas — carrusel de la landing (`#empresas`)

Punto de entrada de los logos del carrusel "Empresas que confían en nosotros"
de `templates/publico/index.html`.

## Estado

17 logos SVG normalizados a monocromo claro. Los archivos crudos de origen se
conservan fuera del repositorio (`odd/assets/logos-originales/`) para
trazabilidad.

## Advertencia de uso (leer antes de publicar)

Estas marcas **no son clientes de JobDevs** y no hay autorización de uso de
marca registrada. Se publican bajo decisión explícita del operador del proyecto
(2026-10-27), presentándolas bajo el titular "Empresas que confían en nosotros".

Riesgo asumido y documentado:

- Publicidad engañosa (Ley 1480 de 2011, Estatuto del Consumidor): afirmar una
  relación comercial inexistente.
- Uso indebido de marca (Decisión Andina 486, Ley 256 de 1996).
- Credibilidad: cualquier empresa o usuario puede verificar que no existe
  relación alguna.
- `dian.svg` corresponde a una **entidad pública** del Estado colombiano, lo
  que agrava el caso respecto de una marca privada.

Para publicar en producción la ruta correcta es: cliente real → autorización
por escrito → registro en la tabla de abajo.

## Registro

| Empresa | Archivo | Fuente | Autorización |
| --- | --- | --- | --- |
| Almacenes Éxito | `almacenes-exito.svg` | Wikimedia Commons | No verificada (decisión del operador, 2026-10-27) |
| Alpina | `alpina.svg` | Wikimedia Commons | No verificada (decisión del operador, 2026-10-27) |
| Bavaria | `bavaria.svg` | Wikimedia Commons | No verificada (decisión del operador, 2026-10-27) |
| Colanta | `colanta.svg` | Wikimedia Commons | No verificada (decisión del operador, 2026-10-27) |
| Colsubsidio | `colsubsidio.svg` | Wikimedia Commons | No verificada (decisión del operador, 2026-10-27) |
| Corona | `corona.svg` | Wikimedia Commons | No verificada (decisión del operador, 2026-10-27) |
| DIAN | `dian.svg` | Wikimedia Commons | No verificada (entidad pública) |
| EPM | `epm.svg` | Wikimedia Commons | No verificada (decisión del operador, 2026-10-27) |
| ETB | `etb.svg` | Wikimedia Commons | No verificada (decisión del operador, 2026-10-27) |
| Ecopetrol | `ecopetrol.svg` | Wikimedia Commons | No verificada (decisión del operador, 2026-10-27) |
| Frisby | `frisby.svg` | Wikimedia Commons | No verificada (decisión del operador, 2026-10-27) |
| Grupo Argos | `grupo-argos.svg` | Wikimedia Commons | No verificada (decisión del operador, 2026-10-27) |
| Olímpica | `olimpica.svg` | Wikimedia Commons | No verificada (decisión del operador, 2026-10-27) |
| Postobón | `postobon.svg` | Wikimedia Commons | No verificada (decisión del operador, 2026-10-27) |
| Presto | `presto.svg` | Wikimedia Commons | No verificada (decisión del operador, 2026-10-27) |
| Rappi | `rappi.svg` | Wikimedia Commons | No verificada (decisión del operador, 2026-10-27) |
| Tiendas D1 | `tiendas-d1.svg` | Wikimedia Commons | No verificada (decisión del operador, 2026-10-27) |

## Normalización aplicada

Cada SVG pasó por este pipeline (reproducible con `magick` + `rsvg-convert`):

1. Eliminación de `<?xml?>`, `<!DOCTYPE>`, `<metadata>` y comentarios.
2. `viewBox` recalculado al contenido real + 1 % de margen (el original de
   Colsubsidio, Corona y Ecopetrol estaba mal calzado y recortaba el trazado).
3. Sin `width`/`height` fijos en la raíz.
4. Inks monocromos: `#c9c9c9`. Los rellenos casi blancos (espacio negativo) se
   mapean a `#0b0b0b` para que la tipografía se lea como calado sobre el fondo
   oscuro.
   - Modo invertido (`#0b0b0b` ↔ `#c9c9c9`), aplicado solo a `tiendas-d1.svg` y
     `frisby.svg`: su recuadro de marca desaparece y queda la tinta clara.
   - `almacenes-exito.svg` y `olimpica.svg` conservan el relleno de marca
     (cobertura 0.75 y 0.91): su recuadro es la identidad del logo y no se puede
     quitar sin redibujarlo. Pendiente decisión: conservarlos o retirarlos del
     carrusel.
5. `currentColor` **no** se usa: un SVG dentro de `<img>` no hereda color del
   documento, así que el tono se controla con `opacity` en CSS.

## Especificación para logos nuevos

- Nombre `<slug>.svg`, minúsculas sin espacios.
- SVG con `viewBox`, sin `width`/`height` fijos, un solo ink.
- Alternativa: PNG transparente, alto ≥ 96 px (ideal 240 px), < 80 KB.
- Peso máximo SVG: 20 KB (test lo valida).
- Sin `<image>` embebido, sin referencias externas.
- `alt` obligatorio con la marca en la pista visible; `alt=""` en la copia.
