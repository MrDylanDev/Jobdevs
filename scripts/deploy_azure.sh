#!/usr/bin/env bash
# ==============================================================================
# JobDevs — Script de Aprovisionamiento y Despliegue en Microsoft Azure
# Stack: Azure Container Apps (ACA) + PostgreSQL 16 Flexible Server + ACR + DataDog
# ==============================================================================

set -euo pipefail

# Colores para salida interactiva
C_RESET='\033[0m'
C_BOLD='\033[1m'
C_GREEN='\033[32m'
C_BLUE='\033[34m'
C_YELLOW='\033[33m'
C_RED='\033[31m'
C_CYAN='\033[36m'

log_info()    { echo -e "${C_BLUE}${C_BOLD}[INFO]${C_RESET} $*"; }
log_ok()      { echo -e "${C_GREEN}${C_BOLD}[OK]${C_RESET} $*"; }
log_warn()    { echo -e "${C_YELLOW}${C_BOLD}[WARN]${C_RESET} $*"; }
log_error()   { echo -e "${C_RED}${C_BOLD}[ERROR]${C_RESET} $*" >&2; }
log_header()  {
    echo -e "\n${C_CYAN}${C_BOLD}============================================================${C_RESET}"
    echo -e "${C_CYAN}${C_BOLD}  $*${C_RESET}"
    echo -e "${C_CYAN}${C_BOLD}============================================================${C_RESET}\n"
}

# ------------------------------------------------------------------------------
# Parámetros de configuración por defecto (pueden sobreescribirse con variables de entorno)
# ------------------------------------------------------------------------------
LOCATION="${AZURE_LOCATION:-eastus}"
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-rg-jobdevs-prod}"
CONTAINERAPPS_ENV="${AZURE_CONTAINERAPPS_ENV:-cae-jobdevs-prod}"
APP_NAME="${AZURE_APP_NAME:-jobdevs-web}"
GITHUB_REPO="${GITHUB_REPOSITORY:-MrDylanDev/Jobdevs}"

# Generador de sufijo aleatorio basado en el ID de suscripción si no se define nombre único
DEFAULT_SUFFIX=$(head /dev/urandom | tr -dc a-z0-9 | head -c 6 || echo "100")
ACR_NAME="${AZURE_ACR_NAME:-acrjobdevs${DEFAULT_SUFFIX}}"
DB_SERVER_NAME="${AZURE_DB_SERVER_NAME:-psql-jobdevs-${DEFAULT_SUFFIX}}"
DB_NAME="${AZURE_DB_NAME:-jobdevs_db}"
DB_USER="${AZURE_DB_USER:-jobdevs_admin}"
DB_SKU="${AZURE_DB_SKU:-Standard_B1ms}" # Tier inicial económico y escalable
DB_STORAGE_SIZE="${AZURE_DB_STORAGE_SIZE:-32}" # GB inicial

# Parámetros de observabilidad con DataDog
DD_SITE="${DATADOG_SITE:-datadoghq.com}"
DD_API_KEY="${DATADOG_API_KEY:-}"

# ------------------------------------------------------------------------------
# Verificación de herramientas
# ------------------------------------------------------------------------------
check_prerequisites() {
    log_info "Verificando herramientas requeridas..."
    if ! command -v az &>/dev/null; then
        log_error "Azure CLI ('az') no está instalado. Podés ejecutar este script en Azure Cloud Shell o instalarlo localmente."
        exit 1
    fi

    # Verificar sesión activa en Azure
    if ! az account show &>/dev/null; then
        log_warn "No hay sesión activa en Azure. Iniciando 'az login'..."
        az login --output none
    fi

    local sub_name sub_id
    sub_name=$(az account show --query name -o tsv)
    sub_id=$(az account show --query id -o tsv)
    log_ok "Sesión activa en Azure: ${C_BOLD}${sub_name}${C_RESET} (${sub_id})"
}

# ------------------------------------------------------------------------------
# 1. Crear Resource Group
# ------------------------------------------------------------------------------
create_resource_group() {
    log_header "1. Resource Group: ${RESOURCE_GROUP}"
    if az group show --name "${RESOURCE_GROUP}" &>/dev/null; then
        log_ok "El Resource Group '${RESOURCE_GROUP}' ya existe."
    else
        log_info "Creando Resource Group '${RESOURCE_GROUP}' en '${LOCATION}'..."
        az group create --name "${RESOURCE_GROUP}" --location "${LOCATION}" --output none
        log_ok "Resource Group creado correctamente."
    fi
}

# ------------------------------------------------------------------------------
# 2. Azure Container Registry (ACR)
# ------------------------------------------------------------------------------
create_acr() {
    log_header "2. Azure Container Registry (ACR): ${ACR_NAME}"
    if az acr show --name "${ACR_NAME}" --resource-group "${RESOURCE_GROUP}" &>/dev/null; then
        log_ok "El ACR '${ACR_NAME}' ya existe."
    else
        log_info "Creando ACR '${ACR_NAME}' (SKU: Basic)..."
        az acr create \
            --resource-group "${RESOURCE_GROUP}" \
            --name "${ACR_NAME}" \
            --sku Basic \
            --admin-enabled true \
            --location "${LOCATION}" \
            --output none
        log_ok "ACR creado exitosamente."
    fi

    ACR_LOGIN_SERVER=$(az acr show --name "${ACR_NAME}" --query loginServer -o tsv)
    log_ok "Servidor de imágenes: ${C_BOLD}${ACR_LOGIN_SERVER}${C_RESET}"
}

# ------------------------------------------------------------------------------
# 3. Azure Database for PostgreSQL 16 Flexible Server
# ------------------------------------------------------------------------------
create_database() {
    log_header "3. PostgreSQL 16 Flexible Server: ${DB_SERVER_NAME}"

    if [ -z "${DB_PASSWORD:-}" ]; then
        if [ -n "${AZURE_DB_PASSWORD:-}" ]; then
            DB_PASSWORD="${AZURE_DB_PASSWORD}"
        else
            log_warn "Generando contraseña segura aleatoria para la base de datos..."
            DB_PASSWORD=$(head /dev/urandom | tr -dc 'A-Za-z0-9!#%*+=' | head -c 24)
            echo -e "${C_YELLOW}${C_BOLD}[IMPORTANTE] Guarda esta contraseña en tu gestor de secretos:${C_RESET}"
            echo -e "   Usuario: ${C_BOLD}${DB_USER}${C_RESET}"
            echo -e "   Clave:   ${C_BOLD}${DB_PASSWORD}${C_RESET}\n"
        fi
    fi

    if az postgres flexible-server show --name "${DB_SERVER_NAME}" --resource-group "${RESOURCE_GROUP}" &>/dev/null; then
        log_ok "El servidor PostgreSQL '${DB_SERVER_NAME}' ya existe."
    else
        log_info "Creando servidor PostgreSQL 16 (Tier: ${DB_SKU}, Storage: ${DB_STORAGE_SIZE}GB)..."
        log_info "Esto puede demorar 2-4 minutos mientras Azure aprovisiona la instancia..."
        az postgres flexible-server create \
            --resource-group "${RESOURCE_GROUP}" \
            --name "${DB_SERVER_NAME}" \
            --location "${LOCATION}" \
            --admin-user "${DB_USER}" \
            --admin-password "${DB_PASSWORD}" \
            --sku-name "${DB_SKU}" \
            --tier Burstable \
            --version 16 \
            --storage-size "${DB_STORAGE_SIZE}" \
            --yes \
            --output none
        log_ok "Servidor PostgreSQL 16 aprovisionado correctamente."

        # Regla de firewall: permitir acceso desde servicios internos de Azure (Container Apps)
        log_info "Configurando regla de firewall para permitir tráfico desde Azure Container Apps..."
        az postgres flexible-server firewall-rule create \
            --resource-group "${RESOURCE_GROUP}" \
            --name "${DB_SERVER_NAME}" \
            --rule-name AllowAllAzureServices \
            --start-ip-address 0.0.0.0 \
            --end-ip-address 0.0.0.0 \
            --output none
        log_ok "Regla de firewall aplicada (0.0.0.0)."

        # Crear base de datos para la aplicación
        log_info "Creando base de datos '${DB_NAME}'..."
        az postgres flexible-server db create \
            --resource-group "${RESOURCE_GROUP}" \
            --server-name "${DB_SERVER_NAME}" \
            --database-name "${DB_NAME}" \
            --output none || true
        log_ok "Base de datos '${DB_NAME}' lista."
    fi

    DB_FQDN=$(az postgres flexible-server show --resource-group "${RESOURCE_GROUP}" --name "${DB_SERVER_NAME}" --query fullyQualifiedDomainName -o tsv)
    log_ok "Host PostgreSQL: ${C_BOLD}${DB_FQDN}${C_RESET}"
}

# ------------------------------------------------------------------------------
# 4. Azure Container Apps Environment
# ------------------------------------------------------------------------------
create_container_env() {
    log_header "4. Azure Container Apps Environment: ${CONTAINERAPPS_ENV}"

    # Instalar o actualizar extensión de Container Apps en Azure CLI si no está
    az extension add --name containerapp --upgrade --yes --output none 2>/dev/null || true

    if az containerapp env show --name "${CONTAINERAPPS_ENV}" --resource-group "${RESOURCE_GROUP}" &>/dev/null; then
        log_ok "El entorno '${CONTAINERAPPS_ENV}' ya existe."
    else
        log_info "Creando Container Apps Environment '${CONTAINERAPPS_ENV}'..."
        az containerapp env create \
            --name "${CONTAINERAPPS_ENV}" \
            --resource-group "${RESOURCE_GROUP}" \
            --location "${LOCATION}" \
            --output none
        log_ok "Container Apps Environment creado."
    fi
}

# ------------------------------------------------------------------------------
# 5. Azure Container App (JobDevs Web)
# ------------------------------------------------------------------------------
create_container_app() {
    log_header "5. Azure Container App: ${APP_NAME}"

    ACR_LOGIN_SERVER=$(az acr show --name "${ACR_NAME}" --query loginServer -o tsv)
    ACR_PASSWORD=$(az acr credential show --name "${ACR_NAME}" --query "passwords[0].value" -o tsv)
    ACR_USERNAME=$(az acr credential show --name "${ACR_NAME}" --query username -o tsv)

    if [ -z "${DJANGO_SECRET_KEY:-}" ]; then
        DJANGO_SECRET_KEY=$(head /dev/urandom | tr -dc 'A-Za-z0-9!@#$%^&*(-_=+)' | head -c 50)
    fi

    # Variables de entorno secretas y públicas para el contenedor
    local env_vars=(
        "DJANGO_SETTINGS_MODULE=config.settings"
        "DJANGO_DEBUG=False"
        "DJANGO_SECURE_PROXY_SSL_HEADER=True"
        "DB_ENGINE=django.db.backends.postgresql"
        "DB_HOST=${DB_FQDN}"
        "DB_PORT=5432"
        "DB_NAME=${DB_NAME}"
        "DB_USER=${DB_USER}"
        "DB_PASSWORD=${DB_PASSWORD:-}"
        "DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}"
        "DD_SITE=${DD_SITE}"
        "DD_SERVICE=jobdevs"
        "DD_ENV=production"
        "DD_VERSION=1.0.0"
    )

    if [ -n "${DD_API_KEY}" ]; then
        env_vars+=("DATADOG_ENABLED=true" "DD_API_KEY=${DD_API_KEY}")
    else
        env_vars+=("DATADOG_ENABLED=false")
    fi

    if az containerapp show --name "${APP_NAME}" --resource-group "${RESOURCE_GROUP}" &>/dev/null; then
        log_ok "La Container App '${APP_NAME}' ya existe. Podés actualizarla con el pipeline de GitHub Actions."
    else
        log_info "Creando Container App '${APP_NAME}' (Puerto 8000, Ingress público)..."
        az containerapp create \
            --name "${APP_NAME}" \
            --resource-group "${RESOURCE_GROUP}" \
            --environment "${CONTAINERAPPS_ENV}" \
            --image "mcr.microsoft.com/azuredocs/aci-helloworld:latest" \
            --target-port 8000 \
            --ingress external \
            --min-replicas 1 \
            --max-replicas 3 \
            --cpu 0.5 \
            --memory 1.0Gi \
            --registry-server "${ACR_LOGIN_SERVER}" \
            --registry-username "${ACR_USERNAME}" \
            --registry-password "${ACR_PASSWORD}" \
            --env-vars "${env_vars[@]}" \
            --output none
        log_ok "Container App creada exitosamente."
    fi

    APP_FQDN=$(az containerapp show --name "${APP_NAME}" --resource-group "${RESOURCE_GROUP}" --query properties.configuration.ingress.fqdn -o tsv)
    log_ok "URL pública asignada: ${C_BOLD}https://${APP_FQDN}${C_RESET}"
}

# ------------------------------------------------------------------------------
# 6. Configurar Autenticación OIDC con GitHub Actions
# ------------------------------------------------------------------------------
setup_github_oidc() {
    log_header "6. Configurar Identidad Federada OIDC para GitHub Actions"

    local app_display_name="github-actions-jobdevs-deploy"
    log_info "Verificando/creando App en Entra ID: ${app_display_name}..."

    local app_id
    app_id=$(az ad app list --display-name "${app_display_name}" --query "[0].appId" -o tsv 2>/dev/null || true)

    if [ -z "${app_id}" ] || [ "${app_id}" = "None" ]; then
        app_id=$(az ad app create --display-name "${app_display_name}" --query appId -o tsv)
        az ad sp create --id "${app_id}" --output none
        log_ok "App y Service Principal creados (App ID: ${app_id})."
    else
        log_ok "App existente encontrada (App ID: ${app_id})."
    fi

    local sub_id tenant_id
    sub_id=$(az account show --query id -o tsv)
    tenant_id=$(az account show --query tenantId -o tsv)

    # Asignar rol Contributor sobre el Resource Group
    log_info "Asignando rol 'Contributor' sobre el Resource Group '${RESOURCE_GROUP}'..."
    az role assignment create \
        --assignee "${app_id}" \
        --role "Contributor" \
        --scope "/subscriptions/${sub_id}/resourceGroups/${RESOURCE_GROUP}" \
        --output none 2>/dev/null || true

    # Asignar rol AcrPush sobre el Container Registry
    log_info "Asignando rol 'AcrPush' sobre ACR '${ACR_NAME}'..."
    local acr_id
    acr_id=$(az acr show --name "${ACR_NAME}" --resource-group "${RESOURCE_GROUP}" --query id -o tsv)
    az role assignment create \
        --assignee "${app_id}" \
        --role "AcrPush" \
        --scope "${acr_id}" \
        --output none 2>/dev/null || true

    # Crear credencial federada para la rama main
    log_info "Configurando credencial federada OIDC para repo: ${GITHUB_REPO} (rama: main)..."
    local cred_body='{
        "name": "jobdevs-github-main",
        "issuer": "https://token.actions.githubusercontent.com",
        "subject": "repo:'"${GITHUB_REPO}"':ref:refs/heads/main",
        "description": "Despliegue continuo desde GitHub Actions main branch",
        "audiences": ["api://AzureADTokenExchange"]
    }'

    az ad app federated-credential create \
        --id "${app_id}" \
        --parameters "${cred_body}" \
        --output none 2>/dev/null || log_warn "La credencial federada ya existe o fue actualizada."

    echo -e "\n${C_GREEN}${C_BOLD}============================================================${C_RESET}"
    echo -e "${C_GREEN}${C_BOLD}  SECRETOS PARA CONFIGURAR EN GITHUB REPOSITORY SECRETS:${C_RESET}"
    echo -e "${C_GREEN}${C_BOLD}  https://github.com/${GITHUB_REPO}/settings/secrets/actions${C_RESET}"
    echo -e "${C_GREEN}${C_BOLD}============================================================${C_RESET}\n"

    echo -e "${C_BOLD}AZURE_CLIENT_ID:${C_RESET}       ${app_id}"
    echo -e "${C_BOLD}AZURE_TENANT_ID:${C_RESET}       ${tenant_id}"
    echo -e "${C_BOLD}AZURE_SUBSCRIPTION_ID:${C_RESET} ${sub_id}"
    echo -e "${C_BOLD}AZURE_ACR_NAME:${C_RESET}        ${ACR_NAME}"
    echo -e "${C_BOLD}AZURE_APP_NAME:${C_RESET}        ${APP_NAME}"
    echo -e "${C_BOLD}AZURE_RESOURCE_GROUP:${C_RESET}  ${RESOURCE_GROUP}"
    if [ -n "${DD_API_KEY}" ]; then
        echo -e "${C_BOLD}DATADOG_API_KEY:${C_RESET}       ${DD_API_KEY}"
    fi
}

# ------------------------------------------------------------------------------
# Resumen general de la arquitectura
# ------------------------------------------------------------------------------
show_summary() {
    log_header "Resumen de la Arquitectura Desplegada"
    echo -e "Resource Group:       ${C_BOLD}${RESOURCE_GROUP}${C_RESET} (${LOCATION})"
    echo -e "Container Registry:   ${C_BOLD}${ACR_NAME}${C_RESET}.azurecr.io"
    echo -e "PostgreSQL 16:        ${C_BOLD}${DB_SERVER_NAME}${C_RESET} (DB: ${DB_NAME}, User: ${DB_USER})"
    echo -e "Container Apps Env:   ${C_BOLD}${CONTAINERAPPS_ENV}${C_RESET}"
    echo -e "Container App Web:    ${C_BOLD}${APP_NAME}${C_RESET}"
    if [ -n "${APP_FQDN:-}" ]; then
        echo -e "URL Pública:          ${C_GREEN}${C_BOLD}https://${APP_FQDN}${C_RESET}"
    fi
    echo -e "Observabilidad:       DataDog APM (${DD_SITE})\n"
}

# ------------------------------------------------------------------------------
# Punto de entrada CLI
# ------------------------------------------------------------------------------
case "${1:-all}" in
    init|all)
        check_prerequisites
        create_resource_group
        create_acr
        create_database
        create_container_env
        create_container_app
        setup_github_oidc
        show_summary
        ;;
    infra)
        check_prerequisites
        create_resource_group
        create_acr
        create_database
        create_container_env
        create_container_app
        show_summary
        ;;
    oidc)
        check_prerequisites
        setup_github_oidc
        ;;
    *)
        echo "Uso: $0 [init|infra|oidc]"
        echo "  init:  Crea toda la infraestructura y configura OIDC de GitHub (recomendado)"
        echo "  infra: Solo crea los recursos de Azure (RG, ACR, Postgres 16, Container App)"
        echo "  oidc:  Solo configura la identidad federada para GitHub Actions"
        exit 1
        ;;
esac
