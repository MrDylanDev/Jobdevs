from .catalogo_views import api_detalle_proyecto, listar_proyectos
from .categorias_views import (
    api_categoria_actualizar,
    api_categoria_crear,
    api_categoria_toggle,
    api_categorias_listar,
)
from .evaluacion_views import calificar_empresa, finalizar_proyecto
from .gestion_views import (
    crear_proyecto,
    desactivar_proyecto,
    editar_proyecto,
    reabrir_postulaciones,
)
from .hitos_equipos_views import (
    eliminar_equipo,
    eliminar_hito,
    gestionar_equipos,
    gestionar_hitos,
)

__all__ = [
    'api_categoria_actualizar',
    'api_categoria_crear',
    'api_categoria_toggle',
    'api_categorias_listar',
    'api_detalle_proyecto',
    'calificar_empresa',
    'crear_proyecto',
    'desactivar_proyecto',
    'editar_proyecto',
    'eliminar_equipo',
    'eliminar_hito',
    'finalizar_proyecto',
    'gestionar_equipos',
    'gestionar_hitos',
    'listar_proyectos',
    'reabrir_postulaciones',
]
