"""
RNF-10 — Escalabilidad: consultas eficientes sobre +10.000 registros.

Verifica que:
1. Las consultas clave de los dashboards usan los índices compuestos
   (EXPLAIN QUERY PLAN sobre SQLite) cuando la tabla supera 10.000 filas.
2. El número de queries emitidas por request permanece acotado
   (sin N+1) independientemente del volumen de datos.
"""
import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.urls import reverse

from contrataciones.models import Contratacion
from postulaciones.models import Postulacion
from proyectos.models import Entregable, Proyecto

User = get_user_model()

pytestmark = pytest.mark.slow


def _seed_masivo(empresa, otras_empresas, total=10001):
    """Crea `total` proyectos repartidos entre varias empresas."""
    proyectos = []
    estados = ['publicado', 'en_desarrollo', 'finalizado', 'inactivo']
    tipos = ['sitio_web', 'aplicacion_movil', 'automatizacion']
    for i in range(total):
        owner = empresa if i % 3 == 0 else otras_empresas[i % len(otras_empresas)]
        proyectos.append(Proyecto(
            empresa=owner,
            titulo=f'Proyecto masivo {i}',
            descripcion='Seed RNF-10',
            tipo_solucion=tipos[i % len(tipos)],
            prioridad='media',
            vacantes=2,
            estado=estados[i % len(estados)],
        ))
    Proyecto.objects.bulk_create(proyectos, batch_size=1000)
    return list(Proyecto.objects.filter(empresa=empresa))


@pytest.fixture
def db_masivo(db, empresa_user):
    """10.001 proyectos + datos relacionados para la empresa bajo prueba."""
    otras = [
        User.objects.create_user(
            username=f'otra_emp_{i}', email=f'otra{i}@jobdevs',
            nombre=f'Otra {i}', rol='empresa', estado='activo',
            password='TestPass123!',
        )
        for i in range(5)
    ]
    mios = _seed_masivo(empresa_user, otras)
    devs = [
        User.objects.create_user(
            username=f'dev_rnf_{i}', email=f'devrnf{i}@jobdevs',
            nombre=f'Dev {i}', rol='desarrollador', estado='activo',
            password='TestPass123!',
        )
        for i in range(3)
    ]
    # Contrataciones activas sobre algunos proyectos en desarrollo
    en_desarrollo = [p for p in mios if p.estado == 'en_desarrollo'][:10]
    for i, p in enumerate(en_desarrollo):
        Contratacion.objects.create(
            proyecto=p, desarrollador=devs[i % 3], empresa=empresa_user,
            estado='activa',
        )
        Entregable.objects.create(
            proyecto=p, titulo=f'Hito {i}',
            estado='completado' if i % 2 == 0 else 'pendiente',
        )
        Postulacion.objects.create(
            proyecto=p, desarrollador=devs[(i + 1) % 3],
            mensaje='postulacion rnf',
            estado='en_negociacion',
        )
    return mios


class TestPlanDeIndices:
    """EXPLAIN QUERY PLAN debe usar los índices compuestos RNF-10."""

    def _plan(self, sql, params=()):
        with connection.cursor() as cur:
            prefix = 'EXPLAIN' if connection.vendor == 'postgresql' else 'EXPLAIN QUERY PLAN'
            cur.execute(f'{prefix} {sql}', params)
            return ' | '.join(str(r[-1]) for r in cur.fetchall())

    def test_listado_publicados_usa_idx_estado_fecha(self, db_masivo):
        plan = self._plan(
            "SELECT id FROM proyectos WHERE estado = %s "
            "ORDER BY fecha_publicacion DESC LIMIT 20",
            ('publicado',),
        )
        assert 'idx_proy_estado_fecha' in plan, plan

    def test_dashboard_empresa_usa_idx_empresa_estado(self, db_masivo):
        plan = self._plan(
            "SELECT id FROM proyectos WHERE empresa_id = %s AND estado = %s",
            (1, 'en_desarrollo'),
        )
        assert 'idx_proy_empresa_estado' in plan, plan

    def test_contratos_empresa_usa_idx_compuesto(self, db_masivo):
        plan = self._plan(
            "SELECT id FROM contrataciones WHERE empresa_id = %s AND estado = %s",
            (1, 'activa'),
        )
        assert 'idx_contratos_empresa_estado' in plan, plan

    def test_hitos_proyecto_usa_idx_compuesto(self, db_masivo):
        plan = self._plan(
            "SELECT id FROM entregables WHERE proyecto_id = %s AND estado = %s",
            (1, 'completado'),
        )
        assert 'idx_entregables_proy_estado' in plan, plan


class TestNumeroDeQueries:
    """El request de los dashboards emite un número acotado de queries."""

    def _count(self, client, url):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as ctx:
            response = client.get(url)
        assert response.status_code == 200
        return len(ctx.captured_queries)

    def test_dashboard_empresa_queries_acotadas(self, db_masivo, auth_client):
        # Con los fixes N+1 (conteo agregado de postulaciones + cache de
        # categorías) el dashboard se mantiene por debajo de 40 queries
        # con 10.001 proyectos y 10 proyectos en desarrollo.
        total = self._count(auth_client, reverse('dashboard_empresa'))
        assert total <= 40, f'{total} queries emitidas (máx esperado 40)'

    def test_listar_proyectos_eficiente(self, db_masivo, auth_client):
        total = self._count(auth_client, reverse('listar_proyectos'))
        assert total <= 12, f'{total} queries emitidas (máx esperado 12)'
