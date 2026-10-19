"""
Tests para el módulo de validación asíncrona de archivos y templates (SCRUM-194).
"""

from usuarios.services_sena import MAX_SOPORTE_DEV_BYTES


class TestFileValidatorIntegration:
    """Verifica la coherencia entre las reglas client-side de file_validator_async.js y el backend."""

    def test_limite_backend_coincide_con_default_client_side(self):
        """El límite de 5MB en backend coincide con los 5MB de file_validator_async.js."""
        assert MAX_SOPORTE_DEV_BYTES == 5 * 1024 * 1024

    def test_templates_incluyen_file_validator_script(self):
        """Los templates principales incluyen file_validator_async.js."""
        templates = [
            'base.html',
            'Desarrollador/Desarrollador.html',
            'empresa/empresa.html',
        ]
        for tpl in templates:
            with open(f'templates/{tpl}', 'r', encoding='utf-8') as f:
                content = f.read()
            assert 'file_validator_async.js' in content, f"Template {tpl} debe cargar file_validator_async.js"

    def test_file_validator_js_estructura_y_reglas(self):
        """El script JavaScript implementa Promesas, FileReader y validación de magic bytes."""
        with open('static/dashboard/script/file_validator_async.js', 'r', encoding='utf-8') as f:
            js = f.read()

        assert 'validarYLeerArchivo' in js
        assert 'leerArchivoAsync' in js
        assert 'new Promise' in js
        assert 'FileReader' in js
        assert '%PDF' in js or '0x25' in js  # Magic bytes de PDF
        assert '0x89' in js                  # Magic bytes de PNG
        assert '0xFF' in js                  # Magic bytes de JPEG
