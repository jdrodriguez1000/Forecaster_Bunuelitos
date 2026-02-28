---
name: model_performance_monitor
description: Gestiona el monitoreo continuo de la precisión del modelo y la salud de los datos post-producción, detectando degradación (drift) y activando protocolos de reentrenamiento.
---

# Skill: Monitor de Salud y Desempeño (Model Monitoring)

Esta habilidad es la encargada de la vigilancia post-despliegue. Su función es asegurar que el modelo "Campeón" mantenga su validez operativa frente a la realidad cambiante de Cafeteria SAS.

## 🌡️ 1. Monitoreo de Precisión Real (Ground Truth)
A diferencia de la validación en entrenamiento, esta habilidad mide el desempeño con datos que el modelo nunca "imaginó":
*   **Comparativa Diaria**: Evaluación de `Predicción(T-1) vs Real(T)`.
*   **Métricas de Desviación**: Cálculo diario del MAPE, MAE y RMSE real.
*   **Umbral Crítico**: Alerta inmediata si el MAPE supera el **12%** en una ventana móvil de 7 días.

## 📉 2. Detección de Drift (Deriva)
Identifica cambios estructurales en el entorno que invalidan el conocimiento del modelo:
*   **Data Drift**: Monitoreo de la distribución de variables exógenas (TRM, Inflación, Precipitaciones). Alerta si los valores actuales se alejan significativamente de los promedios históricos de entrenamiento.
*   **Concept Drift**: Detección de cambios en el comportamiento del consumidor (ej: el impacto de la "Quincena" empieza a diluirse o a desplazarse).

## 🚨 3. Protocolos de Reentrenamiento (Trigger Logic)
La habilidad define cuándo es necesario "volver a la escuela":
*   **Reentrenamiento Programado**: Basado en el `model_lifecycle_manager` (ej: cada 30 días).
*   **Reentrenamiento por Emergencia**: Activado automáticamente si el MAPE real supera el 15% por 3 días consecutivos o si se detecta un Drift crítico en las variables macroeconómicas.

## 📊 4. Reporte de Salud de Fase (Monitoring Report)
Toda auditoría de salud genera un rastro en `outputs/monitoring/` (siguiendo la Persistencia Dual):
*   **`drift_status`**: Estado semáforo (Verde: Estable, Amarillo: Alerta de Drift, Rojo: Degradación Crítica).
*   **`error_trend`**: Gráfico de la evolución del error en el tiempo.
*   **`last_check`**: Timestamp de la última validación de salud.

## 🛡️ 5. Integración con el Storyteller
Si el modelo empieza a fallar, esta habilidad debe informar al `forecasting_storyteller` para que el Informe Ejecutivo incluya una **Verdad Crítica**: *"Atención: El modelo está subestimando la demanda en días de lluvia fuerte debido a un cambio reciente en la logística de domicilios"*.
