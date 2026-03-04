# Blueprint: Phase 03 - Exploratory Data Analysis (EDA)

## 1. 📝 Descripción de la Fase
Esta fase tiene como objetivo transformar el dataset preprocesado en conocimiento accionable y decisiones técnicas para el modelo de forecasting. Se validarán las hipótesis de negocio de **Cafeteria SAS** y se definirán las bases de la ingeniería de características (Lags, Ventanas, Transformaciones) mediante rigor estadístico y analítica avanzada. Es el puente crítico entre los datos limpios y el modelo de alto rendimiento.

## 🏗️ 2. Arquitectura de Ejecución (Plan de Trabajo)

### Bloque A: Control de Calidad y Handshake (Paso 1-3)
1.  **Handshake de Pipeline:** Verificación de éxito de la Fase 02 en la tabla `pipeline_execution_status` de Supabase.
2.  **Parametrización Táctica:** Configuración de la sección `eda` en `config.yaml` (Definición de target, splits anti-leakage y umbrales VIF).
3.  **Carga Inmutable:** Lectura del archivo unificado `data/02_cleansed/master_cleansed_latest.parquet`.

### Bloque B: Rigor Estadístico de Series de Tiempo (Paso 4-8)
4.  **Descomposición STL:** Separación de Tendencia, Estacionalidad y Ruido.
5.  **Análisis de Memoria:** Ejecución de funciones ACF y PACF.
6.  **Test de Estacionariedad:** Aplicación del test Augmented Dickey-Fuller (ADF).
7.  **Análisis de Heterocedasticidad:** Evaluación de la estabilidad de la varianza (análisis post-pandemia).
8.  **Espectrograma de Frecuencia:** Detección de ciclos ocultos o "frecuencias fantasma".

### Bloque C: Validación de Hipótesis de Negocio (Paso 9-11)
9.  **Análisis de Brecha (Gap Analysis):** Comparación entre `demanda_teorica_total` y `ventas_reales` para dimensionar el impacto de los agotados.
10. **Comportamiento Multitemporal:** Análisis de demanda por jerarquías (Día, Mes, Trimestre, Semestre, Año).
11. **Validación de Triggers Estratégicos:**
    *   Regla de los domingos y jerarquía semanal.
    *   Efecto Sábado en Festivos (Mapping validation).
    *   Picos de liquidez (Quincenas y Primas).
    *   Flag de la pandemia (Caracterización del choque).
    *   Ciclo 2x1 y Pauta Digital (Efecto Ads).
    *   Eventos especiales (Feria de las Flores, Semana Santa, Novenas).
    *   Sensibilidad Exógena (Clima y Variables Macroeconómicas).

### Bloque D: Analítica Avanzada e Interacciones (Paso 12-15)
12. **Interacciones Cruciales:** Análisis de efectos combinados (ej: Lluvia + Quincena).
13. **Análisis Lead/Lag:** Caracterización de retardos óptimos para variables externas.
14. **Caracterización de Anomalías:** Clasificación de outliers no explicados por reglas de negocio.
15. **Reducción de Redundancia:** Correlaciones y VIF (Variance Inflation Factor).

## 📊 3. Protocolo de Persistencia (Dual Persistence)
Para garantizar la auditabilidad y el "Wow Factor" de **Triple S**, cada hallazgo visual tendrá un respaldo numérico:
*   **Figures:** Guardadas en `outputs/figures/`.
*   **Analytical Metadata (JSON):** Archivos en `outputs/reports/phase_03/` con los estadísticos (media, mediana, rangos, valores de p) que sustentan cada figura.

## 🚀 4. El "Bridge Report" (Recomendaciones Estratégicas)
El entregable final de la fase es un reporte JSON de recomendaciones vinculantes para la Fase 04:
1.  **Feature Selection:** Variables que se mantienen, se descartan o se transforman (ej: TRM con lag 30).
2.  **Lags & Windows Grid:** Propuesta fundamentada de grids de lags y ventanas rodantes.
3.  **Transformaciones:** Recomendación sobre diferenciación y transformaciones del target (Yeo-Johnson, Log, etc.).
4.  **Scaling Strategy:** Estrategia de normalización/estandarización recomendada.

## 📜 5. Changelog & Historial
*   **2026-03-04:** Creación inicial del Blueprint. Integración del protocolo de 15 puntos de análisis y el motor de recomendaciones técnicas.

---
## ⚖️ 6. Justificación Técnica
Este Blueprint asegura que el proyecto Buñuelitos se mantenga bajo la metodología **First-Prod**. Al separar estrictamente los datos de prueba (185 días) durante el EDA, eliminamos el riesgo de sobreajuste y "Data Leakage". El enfoque en interacciones y análisis de frecuencia permite capturar dinámicas que los métodos tradicionales ignoran, proporcionando a Cafeteria SAS una ventaja competitiva basada en datos reales, no en intuiciones.
