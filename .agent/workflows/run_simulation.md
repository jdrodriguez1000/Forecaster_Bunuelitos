---
description: Ejecuta un análisis de sensibilidad estratégico (What-if) manipulando variables exógenas para evaluar el impacto en la demanda de buñuelos.
---

# Workflow: /run_simulation (Análisis Estratégico)

Este workflow guía al usuario y al agente en la ejecución de simulaciones controladas, asegurando que los cambios en las variables exógenas se procesen de forma aislada y comparable.

## 🚀 Pasos de Ejecución

1.  **Definición del Escenario (UserInput)**:
    *   Nombre del Escenario (ej: "Incremento_Precio_2026").
    *   Variable a Manipular (`precio_unitario`, `inversion_ads`, `dias_promocion`, `inflacion`, etc.).
    *   Magnitud del Cambio (ej: +10%, -500 unidades, etc.).
    *   Horizonte de Simulación (máximo 185 días).

2.  **Activación de la Habilidad `simulation_scenario_manager`**:
    *   El agente utiliza la habilidad para configurar el entorno de simulación.
    *   Se crea un duplicado temporal de las exógenas de la Fase 04 con las modificaciones solicitadas.

3.  **Orquestación de Inferencia Simvía `main.py`**:
    // turbo
    *   Ejecutar el comando de producción con el flag de simulación: `python main.py --mode simulation --scenario "escenario_name"`.

4.  **Generación de Reporte Comparativo (Wow Factor)**:
    *   Invocación de la habilidad `forecasting_storyteller` para crear el visual: **Baseline (Actual) vs. Simulación**.
    *   Cálculo del **Delta de Impacto** (Unidades ganadas/perdidas y valoración económica).

5.  **Documentación en .executive/**:
    *   Redacción automática del Informe Ejecutivo de Simulación.
    *   Estructura: *Impacto de la Decisión*, *Puntos de Poder (Ganancias)* y *Verdades Críticas (Riesgos)*.

6.  **Cierre**:
    *   Aviso al usuario de la ubicación de los resultados en `outputs/simulations/`.
    *   Limpieza de archivos temporales de simulación para no contaminar el historial de producción.

## 🛡️ Reglas de Seguridad
*   Está prohibido que la simulación sobreescriba el modelo "Campeón" (`outputs/models/`).
*   Los resultados de simulación deben guardarse exclusivamente en `outputs/simulations/history/` con el prefijo `sim_`.
*   Toda simulación debe partir obligatoriamente de la última auditoría de salud de datos exitosa (Fase 00).
