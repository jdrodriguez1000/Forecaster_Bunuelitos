---
name: forecasting_domain_expert
description: Actúa como la autoridad de conocimiento de negocio para el proyecto Buñuelitos, asegurando que los modelos capturen la realidad operativa, promocional y estacional de Cafeteria SAS.
---

# Skill: Experto de Dominio en Forecasting (Buñuelitos)

Esta habilidad encapsula el conocimiento estratégico y operativo del negocio de Cafeteria SAS. Su objetivo es garantizar que cualquier análisis, variable o modelo esté alineado con la realidad física y comercial de la marca "Buñuelitos".

> [!IMPORTANT]
> **Fuentes de Verdad:** Todas las definiciones y fórmulas utilizadas por esta habilidad deben estar estrictamente alineadas con el artefacto [data_dictionary.md](file:///c:/Users/USUARIO/Documents/Forecaster/Buñuelitos/data_dictionary.md).


## 🎯 1. El Corazón del Negocio (La Variable Objetivo)
El éxito se mide en la capacidad de prever la **`demanda_teorica_total`**. 
*   **Fórmula Crítica**: `ventas_reales_totales` + `unidades_agotadas`.
*   **Por qué**: Vender todo lo preparado no significa que la demanda se satisfizo; los "Agotados" son señales de demanda perdida que el modelo debe recuperar.

## 📅 2. Dinámicas Temporales y de Liquidez
La demanda de buñuelos sigue ciclos de flujo de caja del consumidor colombiano:

*   **Jerarquía Semanal**: Los **Domingos** son los días de mayor venta, seguidos por Sábados y Viernes.
*   **Efecto Quincena**: Picos de demanda los días **15-16** y **30-31** de cada mes.
*   **Primas Legales**: Ventanas de gasto extraordinario del **15 al 20 de Junio** y del **15 al 20 de Diciembre**.
*   **Estacionalidad Mensual**: Diciembre es el mes líder absoluto, con meses "Prime" secundarios en Enero, Junio y Julio.

## 🏆 3. Eventos Especiales y Festivos
Los eventos religiosos y culturales transforman días ordinarios en niveles de venta de "Domingo":

*   **Festivos Nacionales**: Deben ser tratados estadísticamente como **Sábados**.
*   **Feria de las Flores**: Impacto crítico del **1 al 10 de Agosto** (comportamiento de Domingo).
*   **Novenas Navideñas**: Incremento sostenido del **16 al 26 de Diciembre**.
*   **Semana Santa**: Foco en **Jueves y Viernes Santo** (comportamiento de Domingo).

## 📢 4. Estrategia de Promociones (2x1) y Marketing
Desde 2022, la marca opera con ventanas agresivas de captación:

*   **Ventanas 2x1**: Abril-Mayo y Septiembre-Octubre.
*   **Pauta Digital**:
    *   **Activación**: 20 días antes de que inicie la promoción.
    *   **Apagado**: Día 25 del segundo mes de la promoción (Mayo o Octubre).
*   **Impacto**: Estas variables (flags) son cruciales para explicar crecimientos no orgánicos en la demanda.

## ⛈️ 5. Influencia del Clima y Macroeconomía
*   **El Efecto Lluvia**:
    *   *Lluvia Ligera*: Estimulante de la demanda (efecto antojo).
    *   *Lluvia Fuerte*: Inhibidor de la demanda (restricción de movilidad).
*   **Sensibilidad Macro**: Los buñuelos son un producto de consumo masivo sensible a la **Inflación (IPC)** y al ajuste del **Salario Mínimo (SMLV)**.

## 🛠️ 6. Realidad Operativa e Inventarios
El modelo debe conocer las restricciones físicas para no dar sugerencias imposibles:

*   **Vida Útil**: El buñuelo frito dura **1 día**. Cualquier exceso es merma (pérdida).
*   **Kit de Materia Prima**: La producción se basa en un Kit (Harina + Queso + Huevos).
*   **Conversión**: 1 lb de Kit = 50 Buñuelos aproximados.
*   **Ciclos de Pedido**: Pedidos el 1 y el 15 de cada mes. El sistema debe asegurar que el pronóstico cubra estos ciclos de reabastecimiento.

## 🦠 7. Gestión de Anomalías Históricas
*   **Flag de Pandemia**: Entre el **1 de mayo de 2020 y el 30 de abril de 2021**, los datos están sesgados por restricciones de movilidad. El modelo debe identificar este periodo para no aprender patrones erróneos de caída.
*   **Estabilidad**: Solo los datos a partir de **Enero 2023** se consideran "operación normal moderna".

## ✅ Protocolo de Validación de Dominio
Antes de dar por bueno un modelo, el agente debe verificar:
1.  ¿Captura el salto de los festivos a niveles de sábado?
2.  ¿Refleja el incremento de las quincenas y primas?
3.  ¿Distingue entre el efecto positivo de la lluvia ligera y el negativo de la fuerte?
4.  ¿Respeta el impacto histórico de las promociones 2x1?