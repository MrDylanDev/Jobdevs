# Filtro reactivo de candidatos (panel Empresa)

## Objetivo

Permitir que una empresa filtre las postulaciones recibidas por **nombre**,
**ficha SENA** o **habilidades** sin recargar la página, con un debounce de
300 ms y un mensaje amigable cuando no hay coincidencias.

## Archivos involucrados

| Archivo | Rol |
| --- | --- |
| `templates/postulaciones/lista_recibidas.html` | Expone los datos de cada candidato y monta el buscador en la página completa. |
| `templates/postulaciones/_buscador_candidatos.html` | Partial reutilizable: input, contador, botón limpiar y mensaje de lista vacía. |
| `templates/empresa/empresa.html` | Incluye el partial dentro del drawer de candidatos. |
| `static/empresa/script/candidatos_filtro.js` | Lógica de filtrado en cliente (normalización, debounce, contador, estado vacío). |
| `static/empresa/script/empresa.js` | Clona las tarjetas al abrir el drawer e inicializa/reinicia el filtro. |
| `static/empresa/css/empresa.css` | Estilos del buscador y resaltado de candidatos verificados. |

## Cómo funciona

1. Cada tarjeta de candidato incluye:

   ```html
   <div class="card candidate-card candidato-verificado"
        data-candidato
        data-nombre="..."
        data-ficha="..."
        data-habilidades="..."
        data-verificado-sena="1">
   ```

2. `candidatos_filtro.js` recolecta las tarjetas `.candidate-card` del scope,
   normaliza el texto (minúsculas y sin acentos) y compara contra los tokens
   escritos. Un candidato coincide cuando **todos** los tokens aparecen en la
   concatenación de nombre, ficha y habilidades.

3. El evento `input` se procesa con debounce de 300 ms. Mientras el usuario
   escribe se actualizan:
   - el contador `Mostrando X de Y candidatos`;
   - el botón de limpiar;
   - el mensaje de lista vacía con el término buscado.

4. `Escape` y el botón de limpiar vacían el input y restauran la lista.

## Integración en el drawer

El dashboard de empresa abre las postulaciones en un drawer que descarga
`lista_recibidas.html` y clona las tarjetas. Para que el filtro funcione en
ambos contextos:

- el drawer clona la tarjeta completa (conserva `data-*` y clases);
- el buscador vive fuera de `#drawerContent` para no perderse al reinyectar;
- al abrir el drawer se reinicia el input y, al terminar la carga, se llama a
  `window.inicializarFiltroCandidatos({ scope: contentEl })`.

La función es **idempotente**: si el scope ya fue inicializado solo vuelve a
recolectar tarjetas y reaplica el filtro.

## Accesibilidad

- `role="search"` en el contenedor del buscador.
- `aria-live="polite"` en contador y mensaje de vacío.
- `aria-label` en el botón de limpiar y `sr-only` en la etiqueta del input.

## Cómo extender

Para filtrar por un campo nuevo:

1. Agrega el atributo `data-<campo>` a la tarjeta en `lista_recibidas.html`.
2. Inclúyelo en el arreglo de `recolectarTarjetas()` de
   `candidatos_filtro.js`.
3. Añade una aserción en `TestVerPostulacionesEmpresaFiltros`.

## Pruebas

```bash
uv run --extra dev pytest postulaciones/tests/test_postulaciones.py -q
```

Los tests cubren los atributos de búsqueda, el resaltado de candidatos con
ficha SENA verificada y la presencia del mensaje de lista vacía.
