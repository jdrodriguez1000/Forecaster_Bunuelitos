---
name: forecasting_storyteller
description: Actúa como la autoridad de comunicación visual y estratégica, transformando los resultados técnicos del forecasting en reportes de alto impacto (Wow Factor) para la toma de decisiones gerenciales.
---

# Skill: Storytelling y Visualización Estratégica (Wow Factor)

Esta habilidad es la "cara" del proyecto ante los stakeholders de Cafeteria SAS. Su función es traducir la complejidad de los modelos de Machine Learning en narrativas visuales que generen impacto, confianza y acción estratégica.

## 🎨 1. El Estándar "Wow Factor" (Diseño Premium)
Las visualizaciones no deben ser "genéricas". Deben seguir estos principios estéticos y funcionales:
*   **Paleta de Colores Curada:** Evitar colores básicos. Usar tonos profesionales (azules profundos, naranjas vibrantes para alertas, grises elegantes para históricos).
*   **Anotaciones de Negocio:** Todo pico o caída en la demanda debe estar explicado por un "Trigger" (Festivo, Promoción, Quincena, Clima).
*   **Limpieza Visual:** Eliminar el ruido innecesario. Ejes claros, tipografía legible y uso de áreas sombreadas para representar incertidumbre (intervalos de confianza).

## 📊 2. Gráficos Tácticos Obligatorios (The Triple S Standard)
La habilidad genera visualizaciones estandarizadas en `outputs/figures/` que eliminan la subjetividad política:

### A. La Prueba de Verdad (Venta Real vs. Predicción)
*   **Contenido**: Línea de ventas reales históricas cruzada con la línea del pronóstico (Backtesting).
*   **Wow Factor**: Sombrear el "Intervalo de Confianza". Si la venta real cae dentro de la sombra, el modelo es exitoso.
*   **Métrica Gerencial**: Mostrar en grande el **MAPE %** del periodo visualizado.

### B. El Diagnóstico Operativo (Demanda Teórica vs. Preparados)
*   **Contenido**: Barras de `demanda_teorica_total` comparadas con `buñuelos_preparados`.
*   **Impacto**: Identificar cuándo el negocio perdió dinero por falta de preparación operativa (Agotados) vs. falta de demanda.
*   **Métrica Gerencial**: Expresar el lucro cesante en unidades y proyectar el ahorro si se hubiera seguido el pronóstico.

### C. El Horizonte Estratégico (Forecast 185D)
*   **Contenido**: Visión futura con hitos marcados (Promociones, Novenas, Feria de las Flores).
*   **Propósito**: Anticipación de compras de materia prima (Harina, Queso) alineada a los ciclos de reabastecimiento del Charter.


## 📖 3. Narrativa Estratégica y Reporte Ejecutivo (.executive/)
Esta habilidad es la responsable de redactar el `executive_report_phase_XX.md` siguiendo un estándar de comunicación de alta gerencia. Se prohíbe el lenguaje puramente técnico; la narrativa debe enfocarse en el valor, el riesgo y la oportunidad.

### Estructura Obligatoria del Informe
El informe se divide en dos grandes secciones: **Puntos de Poder** (logros estratégico-técnicos) y **Verdades Críticas** (riesgos o limitaciones descubiertas). Cada punto dentro de estas secciones DEBE seguir este formato:

*   **Nombre:** Título corto, contundente y descriptivo (ej: *Inercia de Quincenas Capturada*).
*   **Frase:** Sentencia profesional que resume el hallazgo (ej: *El flujo de caja de los clientes impulsa el 20% del volumen incremental el día 15*).
*   **Justificación:** Párrafo pedagógico que explica el "porqué" de este dato y cómo beneficia o afecta a Cafeteria SAS.
*   **Evidencia:** El dato exacto (ej: *Coeficiente de correlación = 0.82* o *MAE reducido de 15 a 12 unidades*).
*   **Fuente:** Ubicación exacta del rastro digital (ej: `outputs/reports/phase_03_eda_latest.json` -> campo `correlation_matrix_kpi`).

## 🛡️ 4. Rigor Documental y Auditoría
La habilidad no solo crea; audita que el mensaje sea veraz y coherente:
*   **Consistencia de Datos:** Toda cifra mencionada en el informe de texto DEBE existir en el reporte JSON de la fase correspondiente. Estrictamente prohibido el uso de cifras "estimadas" no trackeadas.
*   **Escalas Coherentes en Visuales:** No truncar ejes para exagerar tendencias en los gráficos de soporte.
*   **Actualidad:** Marcar claramente la "Línea de Hoy" para separar lo Real de lo Pronosticado en los visuales integrados.
*   **Referencia al Contrato:** Toda métrica mostrada (MAE, MAPE) debe coincidir con el reporte oficial de calidad.

## ⚙️ 5. Protocolo de Dual Persistencia (Visual y Narrativa)
Todo artefacto visual y narrativo se guarda doblemente:
*   **Puntero (Latest):** En la raíz de `.executive/` o `outputs/figures/`.
*   **Historial (History):** Versión inmutable en la subcarpeta `history/` con el patrón `nombre_YYYYMMDD_HHMMSS.extension`.

