---
description: Sincroniza el proyecto local con GitHub, crea el repositorio remoto y asegura el despliegue inicial bajo los estándares de MLOps y de Supabase.
---

# Workflow: Deploy GitHub (Forecaster Buñuelitos)

## Pasos de Ejecución

1. **Inicializar Repositorio Local**
   - Comando: `git init -b main`

2. **Verificar Remoto Existente**
   - Comando: `git remote -v`
   - *Decisión*: Si ya existe `origin` apuntando a `Forecaster_Bunuelitos`, saltar al paso 6.

3. **Verificar Existencia en GitHub**
   - Herramienta: `mcp_remote-github_search_repositories`
   - Consulta: `user:@me Forecaster_Bunuelitos`
   - *Decisión*: Si existe, obtener la `clone_url`. Si no, continuar al paso 4.

4. **Crear Repositorio Remoto**
   - Herramienta: `mcp_remote-github_create_repository`
   - Argumentos:
     - `name`: "Forecaster_Bunuelitos"
     - `private`: true
     - `description`: "Proyecto de forecasting para predicción diaria de demanda de buñuelos para Cafetería SAS (Buñuelitos)."

5. **Configurar Origen**
   - Comando: `git remote add origin <CLONE_URL>`

6. **Auditoría de Archivos Temporales y Seguridad**
   - **Acción**: Antes de agregar archivos, identificar y eliminar archivos residuales (`.log`, `.txt` temporales, resultados de pruebas fallidas, archivos de dump).
   - **Verificación de .gitignore**: Asegurar que las siguientes rutas estén ignoradas:
     - `.env`
     - `.venv/`
     - `__pycache__/`
     - `data/` (Solo se sube la estructura, no los datos crudos)
     - `outputs/**/history/` (El historial masivo no se sube a Git)
     - `experiments/` (Los artefactos de laboratorio suelen ser locales)
   - **Limpieza**: Ejecutar `git status` y eliminar manualmente cualquier archivo que no aporte al valor del código fuente o documentación.

7. **Preparación de Archivos (Stage)**
   - Comando: `git add .`

8. **Commit Inicial**
   - Comando: `git commit -m "feat: Estructura inicial del proyecto Buñuelitos y configuración base de MLOps"`

9. **Push a GitHub**
   - Comando: `git push -u origin main`

## Verificación de Integridad
- Confirmar que el repositorio en GitHub refleja la estructura de carpetas definida en el Skill `mlops_infrastructure_architect`.
- Validar que las credenciales de Supabase en `.env` (local) no hayan sido filtradas al repositorio.

---

## 🚦 Salida Esperada
Repositorio `Forecaster_Bunuelitos` activo en GitHub con la estructura oficial del proyecto y sin archivos basura o temporales.
