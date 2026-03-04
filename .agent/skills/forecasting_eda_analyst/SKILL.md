# Skill: Forecasting EDA Analyst

## 1. 🎯 Propósito y Visión
El **Forecasting EDA Analyst** es la autoridad responsable de transformar el dataset preprocesado en un mapa de conocimiento estratégico. Su misión es validar las hipótesis de negocio de **Cafeteria SAS** mediante rigor estadístico, asegurando que solo las señales con verdadero poder predictivo avancen a la fase de ingeniería de características y modelado.

## 🛠️ 2. El Protocolo de Análisis (Paso a Paso)

### Paso 0: Parametrización Táctica
0.  **Configuración del Entorno EDA:** Antes de cualquier ejecución, se debe poblar la sección `eda` en el `config.yaml`. Esto incluye:
    *   **Anti-Leakage Split:** Definir `test_days` (ej. 185 días). El analista **SOLO** tiene permitido ver los datos hasta `T - test_days`. Mirar el set de prueba durante el EDA se considera contaminación y anula el proceso.
    *   **Umbrales Estadísticos:** Definir `vif_threshold` y la lista de columnas para el análisis de multicolinealidad.
    *   **Mapeo de Negocio:** Asegurar que las fechas de pandemia, ciclos de promociones y días especiales (Novenas, Feria de las Flores) coincidan con la realidad operativa de Cafeteria SAS.

### Fase 00: Handshake y Calidad de Entrada
1.  **Validación de Orquestación:** Verificar en la tabla `pipeline_execution_status` de Supabase que la fase de `PREPROCESSING` se ejecutó exitosamente.
    *   **Flujo Principal:** Si `status == 'SUCCESS'`, proceder.
    *   **Flujo Alterno:** Si `status == 'FAILURE'` o no existe registro, detener el proceso y reportar el bloqueo.
2.  **Carga de Configuración:** Leer `config.yaml` para alinear los parámetros de la fase con el estándar del proyecto.
3.  **Lectura de la Verdad:** Cargar el archivo `master_cleansed_latest.parquet` desde `data/02_cleansed/`. Este es el único insumo oficial para el análisis.

### Fase 01: Rigor de Series de Tiempo (Análisis Estadístico)
4.  **Descomposición Clásica:** Separar la serie en **Tendencia, Estacionalidad y Ruido** (STL Decomposition).
5.  **Análisis de Autocorrelación:** Ejecutar **ACF (Autocorrelation Function)** y **PACF (Partial Autocorrelation Function)** para identificar la memoria de la serie.
6.  **Prueba de Estacionariedad:** Aplicar el test de **Augmented Dickey-Fuller (ADF)** para determinar si la serie es apta para modelado directo o requiere diferenciación.
7.  **Estabilidad de la Varianza:** Evaluar la **Heterocedasticidad**. Determinar si la volatilidad cambia con el tiempo (especialmente post-pandemia) y si se requieren transformaciones (Log/Box-Cox).
8.  **Análisis de Frecuencia:** Utilizar Espectrogramas o Transformadas de Fourier para detectar "frecuencias fantasma" (ciclos ocultos de 15, 28 o 30 días).

### Fase 02: Validación de Hipótesis de Negocio
9.  **Interrogación del Target:** Entender la brecha entre la `demanda_teorica_total` y las `ventas_reales`. Identificar patrones de agotados.
10. **Comportamiento Multinivel:** Comprender la demanda por día, mes, trimestre, semestre y año.
11. **El Motor de Hipótesis:**
    *   **Jerarquía Semanal:** Validar la regla `Domingo > Sábado > Viernes`.
    *   **Mapping de Festivos:** Confirmar si los festivos operan como Sábados.
    *   **Picos de Liquidez:** Validar el efecto de las quincenas (15-16, 30-31) y las Primas Legales.
    *   **Anomalía Pandemia:** Caracterizar el impacto del periodo 2020-2021.
    *   **Ciclo de Promoción:** Analizar el antes, durante y después del 2x1 y la pauta de Ads.
    *   **Eventos Críticos:** Evaluar la Feria de las Flores, Semana Santa y Novenas Navideñas.
    *   **Sensibilidad Exógena:** Validar el patrón de Clima (Lluvia Ligera vs Fuerte) y Variables Macro (SMLV, IPC, TRM).

### Fase 03: Analítica Avanzada e Interacciones
12. **Interacciones Cruciales:** Analizar efectos combinados (ej: ¿Cómo afecta la Lluvia cuando cae en Quincena? o ¿Promo en Domingo?).
13. **Análisis de Lead/Lag:** Identificar el rezago temporal de los Ads y variables macro para definir las ventanas de memoria óptimas.
14. **Caracterización de Outliers:** Clasificar anomalías no explicadas (eventos aislados vs cambios estructurales).
15. **Matriz de Relaciones:** Ejecutar Correlación de Spearman/Pearson y **VIF (Variance Inflation Factor)** para detectar multicolinealidad y reducir redundancia.

## 📄 3. Entregables Obligatorios (Outputs)
Al finalizar la fase, el sistema debe producir:
1.  **EDA Figures (Dual Persistence):** Visualizaciones estandarizadas en `outputs/figures/`. Cada figura **DEBE** tener un archivo `.json` homónimo en `outputs/reports/phase_03/` con sus datos estadísticos (medias, medianas, percentiles, etc.).
2.  **Analytical Metadata (JSON):** Archivos de soporte numérico para cada hallazgo visual.
3.  **Executive Report (Wow Factor):** Informe en `.executive/` con las "Verdades Críticas" del negocio.
4.  **Feasibility & Modeling Specs (The "Bridge" Report):** Un reporte JSON detallado que contenga:
    *   **Feature Selection:** Listado de variables que continúan (Keep), las que se descartan (Drop) y las que requieren transformación (ej: TRM con lag de 30 días).
    *   **Lags Grid Recommendation:** Propuesta de grids de lags (ej: `[1, 3, 7, 14]`) basada en el análisis ACF/PACF.
    *   **Rolling Windows Specs:** Definición de ventanas (ej: `[7, 15, 28]`) y funciones (ej: `[mean, std, max]`).
    *   **Stationarity & Transformation:** Recomendación sobre diferenciación y transformaciones del target (Yeo-Johnson, Log, etc.).
    *   **Scaling Strategy:** Recomendación de estandarización/normalización para variables específicas.

## ⚖️ 4. Reglas de Oro del Analista
*   **No Data Leakage:** Está estrictamente prohibido usar información del futuro para el análisis de correlación o validación.
*   **Business First:** Ningún insight estadístico es válido si contradice la lógica de negocio sin una explicación profunda y auditable.
*   **Dual Persistence Mandatory:** Ninguna gráfica existe sin su respaldo en JSON. Si se genera un plot, se genera su metadata.
*   **Actionable Insights:** El EDA no termina en la descripción; termina en la recomendación técnica para la Fase 04 (Ingeniería de Features).
*   **Reproducibilidad:** El análisis debe ser ejecutable vía `main.py` en modo EDA.
