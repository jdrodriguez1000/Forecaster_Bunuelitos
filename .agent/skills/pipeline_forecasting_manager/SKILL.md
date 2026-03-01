---
name: pipeline_forecasting_manager
description: Gestiona la ejecución secuencial del pipeline de forecasting, asegurando la adherencia a la Metodología First-Prod y los estándares de ciencia de datos.
---

# Skill: Gestor del Pipeline de Forecasting (Pipeline Manager)

Esta habilidad dirige el ciclo de vida de un proyecto de forecasting, desde la extracción de datos hasta la generación del pronóstico de negocio, garantizando que el código sea productivo desde su concepción.

## 🔄 Metodología de Ejecución (First-Prod)
En cada fase técnica, el agente debe seguir obligatoriamente este flujo secuencial:

0.  **[EXPLORE]**: Exploración inicial (Fase 00) para definir el **Contrato de Datos**.
1.  **[BLUEPRINT]**: Planificación técnica en `.blueprint/blueprint_phase_XX.md` detallando la lógica y métricas esperadas.
2.  **[CONFIG]**: Parametrización en `config.yaml`. Definición de rutas, hiperparámetros y reglas de negocio.
3.  **[CORE]**: Desarrollo de la lógica en archivos `.py` modulares dentro de `src/`.
4.  **[UNIT-TEST]**: Implementación y aprobación de pruebas unitarias en `tests/unit/` verificando transformadores atómicos.
5.  **[ORCHESTRATE]**: Integración y desarrollo del flujo en el orquestador principal (ej. `main.py`).
6.  **[PROD-OUT]**: Ejecución en terminal para generar reportes y artefactos oficiales en `outputs/`.
7.  **[INTEGRATION-TEST]**: Validación de flujo completo y contratos E2E en `tests/integration/` (Opcional pero recomendado).
8.  **[LAB-WORKFLOW] (OPCIONAL)**: Exploración interactiva en `notebooks/` o mediante `scripts/gen_XX.py`.
9.  **[EXECUTIVE]**: Creación del `executive_report_phase_XX.md` en `.executive/` con el estándar de Puntos de Poder y Verdades Críticas.
10. **[CLOSE]**: Auditoría gerencial, aprobación oficial del usuario y commit final.

## 🔬 Fases del Pipeline de Forecasting

### Fase 00: Exploración Inicial & Contrato de Datos (Data Contract)
*   **Objetivo**: Construir la autoridad de verdad técnica sobre la estructura de los datos. Se ejecuta una sola vez.
*   **Acciones**:
    *   **Lectura Remota**: Lectura de metadatos y muestras de la base de datos sin descarga masiva.
    *   **Definición de Contrato**: Documentación de nombres de columnas, tipos de datos (dtypes), columnas esperadas y métricas base (min/max/unique para numéricos y categorías para objetos).
    *   **Doble Persistencia**: Guardado en `schemas/data_contract_latest.yaml` y copia histórica en `schemas/history/`.
*   **Resultados**: Reporte JSON del Contrato de Datos, actualización de `config.yaml` y creación de archivos YAML en `schemas/`.

### Fase 01: Data Discovery & Audit (Salud de Datos)
*   **Acción**: Conexión a la fuente de datos (Supabase), carga inicial (o incremental) y auditoría de integridad.
*   **Controles Críticos**:
    *   **Data Contract Compliance**: Validar que los datos entrantes cumplen estrictamente con el contrato definido en la Fase 00.
    *   **Salud Estadística**: Identificar nulos, duplicados y huecos temporales (Reindexación diaria inicial).
    *   **Integridad de Negocio**: Verificar consistencia interna de los datos y coherencia entre variables (ej. Ventas vs Inventario).
*   **Resultados**: Reporte de salud de datos y almacenamiento en `data/01_raw/`.

### Fase 02: Preprocesamiento Robusto (Limpieza y Alineación)
*   **Acción**: Transformación de datos crudos en un dataset limpio y alineado temporalmente.
*   **Controles Críticos**:
    *   **Estandarización**: Formateo de nombres y tipos de datos correctos.
    *   **Reindexación Temporal**: Asegurar una frecuencia continua diaria sin saltos.
    *   **Imputación Lógica**: Aplicar reglas de negocio para llenar huecos (ej. ceros para ventas, ffill para macro).
    *   **Anti-Data Leakage**: Eliminar periodos incompletos que puedan sesgar el entrenamiento.
*   **Resultados**: Dataset maestro en `data/02_cleansed/`.

### Fase 03: EDA (Análisis Exploratorio de Datos)
*   **Acción**: Análisis profundo orientado al modelado bajo el principio **"Ojos solo en el Pasado"**.
*   **Controles Críticos**:
    *   **Segmentación**: Análisis exclusivo sobre el set de entrenamiento para evitar fuga de información.
    *   **Estacionariedad**: Pruebas ADF (Dickey-Fuller) y análisis de autocorrelación (ACF/PACF).
    *   **Patrones**: Descomposición estacional y detección de anomalías (Pandemia, Promociones).
*   **Resultados**: Insights de modelado y figuras de soporte en `outputs/figures/`.

### Fase 04: Feature Engineering (Enriquecimiento y Exógenas)
*   **Acción**: Creación de variables explicativas y proyecciones del horizonte futuro.
*   **Controles Críticos**:
    *   **Variables Deterministas**: Indicadores de calendario, quincenas, primas, festivos (Sábados).
    *   **Exógenas Futuras**: Implementación obligatoria de lógica de proyección (185 días) para clima, macro y promociones.
    *   **Marketing (Ads)**: Lógica de activación/desactivación de pauta según calendario de promociones.
*   **Resultados**: Dataset enriquecido en `data/03_features/`.

### Fase 05: Modelado (Optimización y Selección)
*   **Acción**: Entrenamiento competitivo de algoritmos, búsqueda de hiperparámetros y selección del mejor modelo.
*   **Controles Críticos**:
    *   **Tournament**: Competencia entre Ridge, RF, LGBM, XGB, etc. usando `skforecast`.
    *   **Backtesting**: Evaluación mediante validación cruzada temporal con horizonte de 185 días.
    *   **Ljung-Box Test**: Validación de residuos para asegurar captura total de información.
    *   **Champion Model**: Exportación del modelo ganador a `outputs/models/`.
*   **Resultados**: Reporte de experimentos y modelo seleccionado.

### Fase 06: Pronóstico (Producción y Entrega)
*   **Acción**: Ejecución del modelo seleccionado para la generación de predicciones futuras.
*   **Controles Críticos**:
    *   **Inferencia**: Generación de predicciones diarias sobre el horizonte de 185 días.
    *   **MAPE < 12%**: Verificación obligatoria de la métrica de éxito.
    *   **Agregación Mensual**: Fusión de mes actual (Ventas Reales + Predicción) y descarte de meses parciales.
*   **Resultados**: Archivo de pronóstico final en `outputs/forecast/`.

### Fase 07: Simulación (Escenarios What-if)
*   **Acción**: Evaluación del comportamiento de la demanda bajo cambios hipotéticos (What-If).
*   **Controles Críticos**:
    *   **Sensibilidad**: Alteración controlada de precios, duración de promociones, inversión de anuncios o clima.
    *   **Insights Accionables**: Comparativa de escenarios frente al baseline.
*   **Resultados**: Reporte de simulación en `outputs/simulations/`.

### Fase 08: Monitoreo (Salud y Retraining)
*   **Acción**: Seguimiento continuo del desempeño del modelo frente a datos reales.
*   **Controles Críticos**:
    *   **Model Drift**: Detección de degradación en la precisión.
    *   **Alertas**: Definición de umbrales para el reentrenamiento.
*   **Resultados**: Dashboard o reporte de monitoreo en `outputs/monitoring/`.

## 🏗️ 3. Orquestación y Modos de Ejecución
Para garantizar la flexibilidad y eficiencia (evitando reprocesamientos innecesarios), la habilidad debe comandar al orquestador (`main.py`) bajo tres modos principales:

### A. Modo: `load` (Sincronización y Auditoría)
*   **Alcance**: Fase 00 (Contrato) + Fase 01 (Carga Raw).
*   **Uso**: Cuando solo se desea refrescar `data/01_raw/` y verificar la salud de la fuente sin alterar el modelo actual.

### B. Modo: `train` (Ciclo de Modelado Completo)
*   **Alcance**: Fases 02 a 05 (Limpieza, EDA, Features, Modelado).
*   **Uso**: Reentrenamiento periódico o cuando hay cambios en la lógica de ingeniería de variables. Finaliza exportando un nuevo modelo `Candidate` o `Champion`.

### C. Modo: `forecast` (Producción de Inferencia)
*   **Alcance**: Fase 04 (Proyección de Exógenas) + Fase 06 (Inferencia de 185 días).
*   **Uso**: Ejecución diaria operativa. Utiliza el modelo `Champion` existente para generar el pronóstico diario actualizado.

## 🤖 4. Automatización y Resiliencia (Inferencia Permanente)
El pipeline debe estar diseñado para ser "desatendido" (Zero-Touch):
*   **Chequeo de Dependencias**: El orquestador no avanzará a una fase si el artefacto de la fase anterior (ej. `data/02_cleansed/`) es inexistente o tiene un timestamp inválido.
*   **Captura de Logs**: Toda ejecución, sea parcial o total, debe generar un log estructurado para auditoría.
*   **Manejo de Fail-Safe**: Si una ejecución parcial de `forecast` falla, el sistema debe conservar el último pronóstico válido y lanzar una alerta, garantizando que el negocio nunca se quede con "pantalla en blanco".

## 📊 5. Protocolo de Trazabilidad
Cada ejecución genera un artefacto (ej. JSON) bajo el **Patrón de Persistencia Dual**:
*   **Reportes de Negocio (`outputs/reports/`)**
*   **Reportes de Calidad (`tests/reports/`)**

Los archivos JSON deben incluir campos de `phase`, `timestamp`, `metrics` y el `execution_mode` utilizado.

