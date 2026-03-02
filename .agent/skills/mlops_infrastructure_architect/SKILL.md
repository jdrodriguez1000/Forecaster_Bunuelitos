---
name: mlops_infrastructure_architect
description: Define los estándares de ingeniería, jerarquía de almacenamiento y protocolos de calidad para asegurar que los proyectos de forecasting sean reproducibles, modulares y auditables bajo la metodología First-Prod.
---

# Skill: Arquitecto de Infraestructura MLOps (Forecaster Buñuelitos)

Esta habilidad define el ecosistema técnico, la jerarquía de almacenamiento y los protocolos de calidad específicos para el proyecto de pronóstico de demanda de buñuelos. Su objetivo es garantizar que la transición del experimento a la producción sea fluida, auditable y libre de errores de refactorización.

## 📂 1. Estándar de Almacenamiento (Data Layers)
Garantiza la inmutabilidad y el orden del flujo de datos a través de capas lógicas:

*   **`data/01_raw/`**: Datos crudos obtenidos directamente de Supabase. Inmutables una vez descargados para una ejecución específica.
*   **`data/02_cleansed/`**: Datos tras limpieza inicial, estandarización a `snake_case`, tipos de datos correctos y reindexación diaria perfecta (NaN en fechas faltantes).
*   **`data/03_features/`**: Datasets enriquecidos con ingeniería de variables (Quincenas, Primas, Festivos como Sábados, Pandemia, Promociones y proyecciones exógenas de 185 días).
*   **`data/04_processed/`**: Dataset final listo para el entrenamiento del modelo (frecuencia diaria alineada y variables filtradas por el contrato de datos).
*   **`schemas/`**: Directorio de los Contratos de Datos (YAML) bajo protocolo de doble persistencia.
*   **`.blueprint/`**: Planificación técnica obligatoria (Plan de Fase) antes de cada desarrollo.
*   **`.executive/`**: Informes ejecutivos de impacto estratégico (Puntos de Poder y Verdades Críticas).
*   **`experiments/`**: Resultados de laboratorios y notebooks que no deben mezclarse con producción.

## 🏗️ 2. Metodología de Trabajo Industrializada (First-Prod)
El pilar fundamental: la lógica de producción es la base y los notebooks son herramientas opcionales de validación.

1.  **Exploración Inicial ([EXPLORE]):** Fase 00 para definir el **Contrato de Datos** y validar metadatos en Supabase.
2.  **Planificación ([BLUEPRINT]):** Creación del `blueprint_phase_XX.md` detallando la lógica técnica de la fase.
3.  **Configuración ([CONFIG]):** Todo cambio nace en `config.yaml`. Prohibido el uso de valores "hardcoded".
4.  **Core Técnico ([CORE]):** Desarrollo de lógica modular directamente en `src/`.
5.  **Pruebas Unitarias ([UNIT-TEST]):** Validación de componentes atómicos en `tests/unit/`.
6.  **Orquestación de Producción ([ORCHESTRATE]):** Integración en el flujo de `main.py` por fase.
7.  **Salidas Oficiales ([PROD-OUT]):** Generación de reportes JSON y figuras inmutables en `outputs/`.
8.  **Automatización de Laboratorio ([GEN-SCRIPT] - OPCIONAL):** Creación de scripts `scripts/gen_XX.py` que importan de `src/` y generan notebooks para validación visual.
9.  **Pruebas de Integración ([INTEGRATION-TEST]):** VALIDACIÓN E2E del flujo y cumplimiento del contrato de datos.
10. **Informe Ejecutivo ([EXECUTIVE]):** Documentación del impacto en `.executive/` con evidencia numérica exacta.
11. **Cierre y Auditoría ([CLOSE]):** Aprobación explícita del usuario y commit final del hito.

## 💻 3. Arquitectura de Código (`src/`)
Diseño orientado a objetos y modularidad técnica:

1.  **`src/connectors/`**: Cliente de conexión a Supabase y gestión de sesiones.
2.  **`src/loader.py`**: Extracción y validación rigurosa contra el **Contrato de Datos**.
3.  **`src/preprocessor.py`**: Limpieza, reindexación temporal diaria e imputación lógica.
4.  **`src/analyzer.py`**: Análisis Exploratorio de Datos (EDA) orientado al modelado.
5.  **`src/features.py`**: Ingeniería de variables: Calendario, Festivos y proyecciones futuras.
6.  **`src/models.py`**: Entrenamiento competitivo (skforecast) y optimización.
7.  **`src/forecaster.py`**: Inferencia diaria de 185 días y agregación mensual.
8.  **`src/simulator.py`**: Lógica de simulaciones "What-if".
9.  **`src/monitor.py`**: Métricas de salud del modelo y detección de drift.
10. **`src/utils/`**: Helpers para logging y gestión de archivos.

## ✅ 4. Capa de Calidad y QA (`tests/`)
Protocolos de validación obligatorios usando `pytest`:
*   **Tests Unitarios**: En `tests/unit/` para lógica de transformación y carga.
*   **Tests de Integración**: En `tests/integration/` para asegurar que el pipeline corre de punta a punta.
*   **Reportes de Calidad**: Todo test genera un JSON en `tests/reports/` bajo el **Protocolo de Dual Persistencia**.

## 📊 5. Segregación de Salidas y Protocolo de Trazabilidad (Dual Persistencia)

### 🛠️ Herramientas de Scripting y Utilidades
*   **`scripts/explorer.py`**: Script dedicado exclusivamente a la exploración inicial y construcción del **Contrato de Datos**.
*   **`main.py`**: Orquestador principal que invoca las clases de `src/` según la fase.
*   **`scripts/gen_XX.py`**: Generadores de notebooks experimentales (opcional).

### 🏭 Producción y Documentación
Toda salida oficial debe persistirse doblemente:
*   **Latest**: Archivo en la raíz de la subcarpeta (ej: `outputs/reports/phase_01_latest.json`).
*   **History**: Versión inmutable en `/history/` con timestamp (ej: `outputs/reports/history/phase_01_20260228.json`).

Subcarpetas oficiales con este protocolo:
*   **`outputs/reports/`**: Reportes JSON con métricas de fase.
*   **`.blueprint/`**: Planeación técnica inmutable.
*   **`.executive/`**: Informes ejecutivos estratégicos.
*   **`outputs/figures/`**: Visualizaciones (PNG/HTML).
*   **`outputs/models/`**: Binarios (.pkl/.joblib).
*   **`outputs/forecast/`**: Pronóstico diario final (.csv).
*   **`outputs/simulations/`**: Resultados de escenarios What-if.

### 📜 Esquemas y Gobernanza (`schemas/`)
Los contratos de datos siguen el protocolo de dualidad:
*   **Latest**: `schemas/data_contract_latest.yaml`.
*   **History**: `schemas/history/data_contract_YYYYMMDD_HHMM.yaml`.

### 🔬 Laboratorio y Opcionales
*   **`notebooks/`**: Exploraciones interactivas (Fase opcional).
*   **`experiments/`**: Resultados de laboratorios y notebooks (figuras, tablas temporales, logs) que NO deben mezclarse con producción.

## ⚙️ 6. Estándares de Configuración
*   **Zero Hardcoding**: Solo se permite el uso de variables definidas en `config.yaml`.
*   **Semilla Transversal**: Uso obligatorio de `random_state=42` para garantizar reproducibilidad.
*   **Entorno**: Un solo `.venv` referenciado por `requirements.txt`.
