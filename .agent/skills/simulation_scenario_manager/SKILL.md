---
name: simulation_scenario_manager
description: Define los protocolos de experimentación estratégica y análisis de sensibilidad (What-if) para evaluar el impacto de cambios controlados en variables exógenas sobre la demanda de buñuelos.
---

# Skill: Gestor de Escenarios de Simulación (Simulation Manager)

Esta habilidad actúa como el motor de experimentación estratégica del proyecto. Su objetivo es transformar el modelo predictivo en una herramienta de decisión mediante la alteración controlada de variables externas para responder preguntas críticas de negocio.

## 🧪 1. El Protocolo "What-If" (Fase 07)
Toda simulación debe partir de un punto de comparación inmutable para ser válida:
*   **Pronóstico Baseline**: El resultado estándar del modelo usando las proyecciones más probables de las exógenas (Fase 06).
*   **Escenario Perturbado**: El resultado del mismo modelo, pero con una o más variables exógenas modificadas según una hipótesis de negocio.
*   **Regla de Oro**: Se prohíbe reentrenar el modelo para una simulación; solo se permite la alteración de las entradas futuras del horizonte de 185 días.

## 🏗️ 2. Arquetipos de Simulación (Escenarios Pre-definidos)
Basados en el Project Charter, estos son los experimentos mandatorios:

### A. Sensibilidad de Precio
*   **Pregunta**: ¿Cómo afecta un cambio en el `precio_unitario` el volumen de venta?
*   **Perturbación**: Ajustes porcentuales ($\pm 5\%$, $10\%$, $15\%$) sobre el precio base proyectado.
*   **Control**: Mantener el resto de variables (Marketing, Macro) constantes.

### B. Dinámica de Promociones (2x1)
*   **Pregunta**: ¿Qué impacto tiene extender la promoción 10 días adicionales o mover sus fechas de inicio?
*   **Perturbación**: Alterar el flag `es_promocion` y ajustar la ventana de pauta (`ads_activos`) siguiendo la regla de "20 días antes de inicio y apagado el día 25 del segundo mes".
*   **Validación**: Asegurar que la pauta publicitaria se mueva en sincronía con la fecha de la promoción.

### C. Estrés Macroeconómico
*   **Pregunta**: ¿Cuál es el riesgo ante una inflación (IPC) alta o un aumento súbito del SMLV?
*   **Perturbación**: Incrementar los indicadores macroeconómicos en el horizonte futuro para observar la elasticidad de la demanda.

### D. Eventos Climáticos (Shock)
*   **Pregunta**: ¿Cuánto impacta una semana de lluvias fuertes persistentes?
*   **Perturbación**: Modificar el `tipo_lluvia` a "Fuerte" y la `precipitacion_mm` para un periodo específico del horizonte de pronóstico.

## 📊 3. Comparativa y Métricas de Impacto
Los resultados de la simulación deben presentarse en términos de variación respecto al Baseline:
*   **Delta de Unidades ($\Delta U$):** Diferencia absoluta en buñuelos pronosticados.
*   **Variación Porcentual ($\Delta \%$):** Sensibilidad relativa de la demanda ante el cambio.
*   **Impacto en Facturación (Estimado):** Cruzar el pronóstico de unidades con el nuevo `precio_unitario` simulado.

## 🛠️ 4. Reglas Técnicas de Inyección
Para cada simulación, el script `src/simulator.py` o los artefactos correspondientes deben:
1.  **Clonar** el dataset de variables enriquecidas (`data/03_features/`) generado en la Fase 04.
2.  **Inyectar** los cambios en las columnas correspondientes respetando la coherencia técnica.
3.  **Ejecutar** el modelo pre-seleccionado (`outputs/models/champion_latest.pkl`).
4.  **Exportar** la comparativa JSON y gráfica a `outputs/simulations/`.

## 📑 5. Documentación de Hallazgos
Cada ejecución de simulación debe generar un reporte bajo el **Patrón de Persistencia Dual** que incluya:
*   **Hipótesis**: Qué variable se cambió y por qué.
*   **Magnitud de Perturbación**: El valor exacto del cambio (ej: +10% precio).
*   **Respuesta de Demanda**: Los resultados clave (Insights).
*   **Conclusiones Estratégicas**: Recomendaciones para la gerencia de Cafeteria SAS.
