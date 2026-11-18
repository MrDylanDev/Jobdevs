# Despliegue de JobDevs en Microsoft Azure y DataDog

Esta guía documenta la arquitectura y el procedimiento paso a paso para desplegar **JobDevs** en **Microsoft Azure** utilizando **Azure Container Apps (ACA)**, **Azure Database for PostgreSQL 16 Flexible Server**, **Azure Container Registry (ACR)** y monitoreo con **DataDog (APM & Métricas)**.

---

## 1. Arquitectura de Despliegue

```
                           Internet / Usuarios
                                  │
                                  ▼ (HTTPS / TLS administrado)
               ┌──────────────────────────────────────┐
               │    Azure Container Apps Ingress     │
               └──────────────────┬───────────────────┘
                                  │ (Reverse Proxy Envoy)
                                  ▼ (Puerto 8000)
    ┌───────────────────────────────────────────────────────────────┐
    │ Azure Container Apps Environment (cae-jobdevs-prod)           │
    │                                                               │
    │   ┌───────────────────────────────────────────────────────┐   │
    │   │  Contenedor JobDevs Web (Gunicorn + ASGI + WhiteNoise) │   │
    │   │  • Python 3.14 + Tesseract OCR                        │   │
    │   │  • ddtrace-run (DataDog APM & Traces)                │   │
    │   └──────────────────────┬────────────────────────────────┘   │
    └──────────────────────────┼────────────────────────────────────┘
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
┌───────────────────────────────┐   ┌───────────────────────────────┐
│ PostgreSQL 16 Flexible Server │   │ DataDog Cloud (Datadoghq.com) │
│ • Tier: Burstable Standard_B1ms│   │ • APM (Trazas distribuidas)   │
│ • Base: jobdevs_db            │   │ • Tiempos de query PostgreSQL │
│ • Firewall: Azure Services OK │   │ • Errores 5xx correlacionados │
└───────────────────────────────┘   └───────────────────────────────┘
```

---

## 2. Prerrequisitos

1. **Suscripción de Azure:** con permisos de Contributor o Owner.
2. **Azure CLI (`az`):** instalado localmente o utilizando **Azure Cloud Shell** directamente en [portal.azure.com](https://portal.azure.com).
3. **Cuenta de DataDog (Opcional pero recomendada):** con una `API Key` generada en *Organization Settings -> API Keys*.

---

## 3. Aprovisionamiento Automático con Azure CLI

El repositorio incluye el script `scripts/deploy_azure.sh` para crear todos los recursos de infraestructura y configurar la identidad federada con GitHub Actions.

### Opción A: Desde Azure Cloud Shell (Recomendada — Sin instalar nada local)

1. Abrí [portal.azure.com](https://portal.azure.com) e iniciá sesión.
2. Abrí la terminal **Cloud Shell** (ícono `>_` arriba a la derecha) seleccionando entorno **Bash**.
3. Cloná el repositorio o subí el script:
   ```bash
   git clone https://github.com/MrDylanDev/Jobdevs.git
   cd Jobdevs
   git checkout feat/deploy-azure-datadog
   ```
4. Ejecutá el script de inicialización:
   ```bash
   # Podés pasar tu API Key de DataDog si la tenés a mano:
   export DATADOG_API_KEY="tu_datadog_api_key"
   export DATADOG_SITE="datadoghq.com" # o us5.datadoghq.com

   ./scripts/deploy_azure.sh init
   ```

El script realizará de forma automática e idempotente:
* Creación del **Resource Group** (`rg-jobdevs-prod` en `eastus`).
* Creación del **Azure Container Registry** (`acrjobdevs...`).
* Creación del **PostgreSQL 16 Flexible Server** (`Standard_B1ms`) con firewall configurado para Azure.
* Creación del **Container Apps Environment** y la **Container App**.
* Creación del Service Principal en Microsoft Entra ID con **Federación OIDC** para GitHub Actions.

Al finalizar, el script mostrará en pantalla los secretos listos para copiar.

---

## 4. Configurar Secretos en GitHub Actions

En tu repositorio de GitHub, ingresá a:
**Settings -> Secrets and variables -> Actions -> New repository secret**

Agregá los siguientes secretos reportados por el script:

| Nombre del Secreto | Descripción |
| :--- | :--- |
| `AZURE_CLIENT_ID` | Application (Client) ID de la App registrada en Entra ID. |
| `AZURE_TENANT_ID` | Directory (Tenant) ID de tu suscripción de Azure. |
| `AZURE_SUBSCRIPTION_ID` | ID de tu suscripción de Azure. |
| `AZURE_ACR_NAME` | Nombre de tu Azure Container Registry (ej: `acrjobdevs123`). |
| `AZURE_APP_NAME` | Nombre de tu Container App (ej: `jobdevs-web`). |
| `AZURE_RESOURCE_GROUP` | Nombre del Resource Group (ej: `rg-jobdevs-prod`). |
| `DATADOG_API_KEY` | *(Opcional)* API Key de DataDog para marcadores de despliegue. |
| `DATADOG_SITE` | *(Opcional)* Dominio DataDog (`datadoghq.com` por defecto). |

---

## 5. Despliegue Continuo (CI/CD)

El archivo `.github/workflows/deploy.yml` se dispara automáticamente en cada `push` a la rama `main` (o manualmente desde la pestaña **Actions -> Deploy to Azure Container Apps -> Run workflow**).

El pipeline ejecuta:
1. Autenticación Passwordless contra Azure con **OpenID Connect (OIDC)** mediante `azure/login@v2`.
2. Compilación de la imagen Docker en la nube con `az acr build`.
3. Despliegue sin caída de servicio (*zero-downtime*) en Azure Container Apps con `azure/container-apps-deploy-action@v2`.
4. Ejecución automática de `python manage.py migrate --noinput` en la nueva revisión.
5. Emisión de un evento de despliegue hacia DataDog.

---

## 6. Verificación Post-Despliegue

1. **Navegación web:** Accedé a la URL pública reportada por Azure (ej: `https://jobdevs-web.<region>.azurecontainerapps.io`).
2. **Archivos estáticos:** Verificá que los estilos e imágenes carguen correctamente; WhiteNoise los sirve directamente desde el contenedor con compresión Brotli/Gzip.
3. **DataDog APM:**
   - Ingresá a DataDog -> **APM -> Services -> `jobdevs`**.
   - Vas a ver la tasa de peticiones, latencias (p50, p95, p99), errores HTTP y llamadas a PostgreSQL y Redis.
