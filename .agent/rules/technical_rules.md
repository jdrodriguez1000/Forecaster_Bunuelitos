---
trigger: always_on
---

# Technical Rules & Standards: Forecaster Buñuelitos

Este documento define la arquitectura técnica, los estándares de ingeniería de software y los protocolos de persistencia del proyecto. Es el manual de construcción para asegurar una solución robusta e industrial.

---

## 🏗️ 1. Arquitectura y Stack Tecnológico
*   **Orquestación:** Coordinación obligatoria entre `project_charter.md`, `strategic_rules.md`, `business_rules.md` y las habilidades en `.agent/skills/`.
*   **Librería Core:** `skforecast` (ForecasterDirect).
*   **Modelos Autorizados:** Ridge, RandomForest, LGBM, XGB, GradientBoosting, HistGradientBoosting.
*   **Gestión de Configuración:** Uso estricto de `config.yaml`. Prohibido el uso de valores "hardcoded" en el código productivo (`/src/`).

## 🛠️ 2. Estándares de Ingeniería de Datos (Clean Data Laws)
*   **Persistencia Maestra:** Supabase (PostgreSQL). Tablas: `ventas`, `inventario`, `finanzas`, `marketing`, `macroeconomia`, `clima`.
*   **Deduplicación:** En caso de registros redundantes, se aplicará el principio de "Última Verdad" (conservar el registro con el timestamp más reciente).
*   **Continuidad Temporal (Reindexación):** La serie de tiempo debe ser continua día a día. Los días faltantes en la base de datos se crean inicialmente con `NaN`.
*   **Imputación:** La lógica de imputación (ceros para ventas, interpolación para clima/macro) ocurre estrictamente en la fase de `preprocessing`, nunca en la carga inicial.

## 📂 3. Estándares de Salida y Segregación
Queda prohibido mezclar capas de experimentación con producción:

### 3.1. Directorios de Producción (`outputs/`)
*   **Reportes:** `outputs/reports/phase_XX/` (Archivos JSON oficiales).
*   **Figuras:** `outputs/figures/` (Gráficos estandarizados).
*   **Modelos:** `outputs/models/` (Binarios .pkl/.joblib).
*   **Pronósticos:** `outputs/forecast/` (CSV de resultados diarios).

### 3.2. Capa de Trazabilidad (Dual Persistence)
Todo artefacto oficial debe seguir el patrón de doble guardado:
*   **Latest:** El puntero actual para uso del sistema (ej: `model_champion_latest.pkl`).
*   **History:** El archivo inmutable de auditoría con timestamp (ej: `history/model_20260228_1500.pkl`).

## ⚙️ 4. Protocolos de Desarrollo y Código
*   **Idioma:** Código, funciones, variables y estructura de directorios en **Inglés**. Lógica de negocio y documentación en **Español**.
*   **Entorno:** Uso exclusivo de `.venv` gestionado por `requirements.txt`.
*   **Integración Continua:** Cada fase debe pasar por el `quality_assurance_manager` antes de considerarse terminada.

## 📄 5. Formatos de Documentación Técnica
*   **Blueprint:** Debe almacenarse en `.blueprint/` y seguir la estructura de descripción, arquitectura, changelog y justificación técnica.
*   **Executive Report:** Debe almacenarse en `.executive/` y cumplir con el formato de "Puntos de Poder" y "Verdades Críticas" con fuentes de datos linkeadas dinámicamente.

## ⚖️ 6. Protocolo de Calidad (Safe-Zone)
*   **Aislamiento de Tests:** Los frameworks de prueba no pueden modificar el contenido de las carpetas de producción (`outputs/`). Deben correr en un entorno de "Sandbox" o usar flags de simulación.
*   **Gobernanza de Modelos:** La promoción a "Modelo Campeón" no es automática. Debe basarse en criterios de MAPE y mejora porcentual sobre el modelo anterior registrados en el Model Registry.
