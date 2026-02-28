---
name: model_lifecycle_manager
description: Gestiona el ciclo de vida, la jerarquía de versiones y la gobernanza de los modelos de forecasting, asegurando la trazabilidad entre binarios (.pkl) y metadatos estratégicos.
---

# Skill: Gestor de Ciclo de Vida de Modelos (Forecaster Buñuelitos)

Esta habilidad actúa como el **Model Registry** del proyecto. Su misión es asegurar que cada iteración del modelo sea auditable, reproducible y que la promoción al estado de "Campeón" (Producción) se base en criterios técnicos objetivos.

## 📋 1. El Concepto de "Model Card" (Ficha Técnica)
Cada modelo generado debe ir acompañado de un archivo de metadatos estandarizado que incluya:

*   **Identidad:** Versión, Timestamp, Arquitectura (ej: LGBMRegressor via ForecasterDirect).
*   **Linaje (Lineage):** Hash del dataset de entrenamiento (vinculado a la Fase 00) y versión del código en `src/models.py`.
*   **Hiperparámetros:** Configuración exacta utilizada en `GridSearchCV` o `RandomSearchCV`.
*   **Performance (Métricas):** MAE, MAPE, RMSE desglosados por horizontes (corto vs largo plazo) y por tipos de día (Festivos vs Laborales).

## 🚀 2. Estados del Ciclo de Vida
La habilidad gestiona la transición del modelo a través de estos estados:

1.  **`Experimental`**: Modelos nacidos en notebooks o pruebas rápidas. No entran al registro oficial de `outputs/`.
2.  **`Candidate`**: Modelos entrenados en el flujo oficial de `main.py` que han superado las pruebas unitarias.
3.  **`Champion` (Latest)**: El modelo que actualmente domina la producción. Es el puntero que utiliza el `forecaster.py` para generar el pronóstico de 185 días.
4.  **`Archived` (History)**: Modelos que fueron campeones pero han sido superados. Se conservan para auditoría y análisis de degradación.

## ⚖️ 3. Protocolo de Promoción (The Challenger Logic)
Para que un modelo `Candidate` reemplace al `Champion`, la habilidad debe validar:
*   **Criterio de MAPE:** El error debe ser inferior al 12% global (Regla de Oro).
*   **Criterio de Mejora:** Debe ser estadísticamente superior (o más ligero/veloz) al campeón actual.
*   **Criterio de Resiliencia:** No debe presentar errores grotescos en fechas críticas (Novenas, Feria de las Flores).

## 📊 4. Dual Persistencia y Registro
*   **Sincronía Obligatoria:** Por cada `.pkl` en `outputs/models/`, debe existir un `.json` con el mismo nombre exacto.
*   **Registro Histórico:** Mantenimiento de un archivo `model_registry_inventory.json` que actúa como el índice maestro de todos los modelos "Candidatos" y "Campeones" de la historia del proyecto.

## 🛡️ 5. Auditoría de Inferencia
Al momento de realizar un pronóstico, la habilidad debe:
1.  Verificar que el modelo `Latest` cargado coincida con los metadatos registrados.
2.  Emitir una alerta si el modelo tiene más de 30 días sin ser reentrenado (Detección de obsolescencia).
