# Base de Datos — JobDevs

## Arquitectura
La base de datos principal de JobDevs es **PostgreSQL 16**.

### Inicialización y Migraciones
El esquema de base de datos se genera y mantiene exclusivamente a través del sistema de migraciones nativo de Django:

```bash
# Aplicar migraciones para crear o actualizar el esquema
python manage.py migrate
```

### Datos de prueba para desarrollo
Para sembrar cuentas de prueba y perfiles limpios (sin información confidencial ni dependencias externas), ejecutar:

```bash
python manage.py seed_demo_data
```

Esto generará:
- **Administrador:** `admin_demo`
- **Empresa:** `empresa_demo`
- **Desarrollador:** `dev_demo`
- Contraseña por defecto: `Jobdevs2026*`

### Archivo legado `database/init.sql`
El archivo `init.sql` se conserva únicamente como referencia histórica del esquema relacional DDL original de MySQL. No se monta en los contenedores ni contiene credenciales o datos de producción.
