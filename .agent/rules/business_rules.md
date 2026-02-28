---
trigger: always_on
---

# Business & Data Science Rules: Forecaster Buñuelitos

Este documento contiene el rigor analítico y el conocimiento de dominio que alimenta los modelos de forecasting. Es la guía para asegurar que la Ciencia de Datos sea fiel al negocio de Cafeteria SAS.

---

## 1. 🔬 Definición de la Inteligencia (Variable Objetivo)
*   **Variable Target:** `demanda_teorica_total`.
*   **Composición:** Es una variable reconstruida: `ventas_reales_totales` + `unidades_agotadas`.
*   **Importancia:** Modelar solo las ventas reales escondería la demanda insatisfecha. El forecasting debe predecir lo que el cliente *quería comprar*, no solo lo que *logró comprar*.

## 🛡️ 2. Reglas Anti-Leakage y Ética de Datos
*   **Frenado Temporal:** Para predecir el día $T$, el modelo solo puede ver información hasta las 23:59:59 del día $T-1$. El uso de cualquier dato del mismo día de la predicción se considera "contaminación" (Leakage) y anula el modelo.
*   **Independencia Exógena:** No se pueden usar variables que sean consecuencia de la demanda (ej: ahorro en costos operativos del día $T$) para predecir dicha demanda.

## 📅 3. Horizonte y Estacionalidades Estratégicas
*   **Horizonte de Predicción:** Un bloque continuoizado de **185 días**.
*   **Tratamiento de Reporte:** Los reportes mensuales deben fusionar la historia real con la predicción.
*   **Regla Visual:** Descartar meses calendario finales si el horizonte de 185 días no los cubre por completo, evitando distorsiones visuales en gráficos de barras o líneas.

## 🧠 4. Lógica de Features (El Calendario de Operación)
El modelo debe integrar obligatoriamente las siguientes dinámicas:

### 4.1. Eventos Críticos y Anomalías
*   **Efecto Pandemia:** Flag del `01/05/2020` al `30/04/2021`. Representa una distorsión estructural de la demanda.
*   **Promociones 2x1:** Abril-Mayo y Septiembre-Octubre (desde 2022). Son los periodos de mayor captación y volumen.
*   **Novenas de Aguinaldos:** Del `16 al 26 de Diciembre`. Periodo de pico máximo estacional por tradición cultural.

### 4.2. Comportamiento de Tráfico (Mappings)
*   **Festivos Nacionales:** Deben modelarse estadísticamente como **Sábados**.
*   **Feria de las Flores (01-10 Agosto):** Operación y demanda nivel **Domingo**.
*   **Semana Santa (Jueves y Viernes Santo):** Operación y demanda nivel **Domingo**.
*   **Jerarquía Semanal:** Domingo > Sábado > Viernes > Otros días.

### 4.3. Ciclos de Liquidez (Efecto Bolsillo)
*   **Quincenas:** Picos en los días `15-16` y `30-31` de cada mes.
*   **Primas Legales:** Ventanas de gasto extraordinario del `15 al 20 de Junio` y del `15 al 20 de Diciembre`.

## 📢 5. Reglas de Marketing y Clima
*   **Pauta Digital (Ads):** Se activan **20 días antes** del inicio de una gran promoción y se apagan el **día 25 del segundo mes** de la misma campaña.
*   **Efecto Clima (Sensibilidad):**
    *   **Lluvia Ligera (+):** Incrementa el consumo de productos calientes y el "antojo".
    *   **Lluvia Fuerte (-):** Destruye el tráfico peatonal y reduce las ventas en calle.

## 🔬 6. Rigor en Validación
*   **Partición:** Time Series Cross Validation con escenario ciego de 185 días.
*   **Exógenas Futuras:** Proyección mediante promedios móviles, heurísticas de negocio o Forward Fill para asegurar que el modelo pueda "mirar" 6 meses hacia adelante con datos razonables.
*   **Semilla Obligatoria:** `random_state=42` para garantizar que los modelos sean reproducibles y auditables.
