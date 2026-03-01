# Diccionario Técnico-Negocio: Proyecto Buñuelitos

Este documento es la autoridad única de definiciones para el proyecto de forecasting de Cafeteria SAS. Cualquier término utilizado en reportes ejecutivos, visualizaciones o código debe adherirse estrictamente a estas definiciones.

---

## 🎯 1. Variables de Negocio (Core Metrics)

| Término | Definición Técnica | Relevancia de Negocio |
| :--- | :--- | :--- |
| **Demanda Teórica Total** | `ventas_reales_totales` + `unidades_agotadas` | **Variable Objetivo (Target)**. Representa el apetito total del mercado, independientemente de si hubo producto o no. |
| **Unidades Agotadas** | Demanda no satisfecha registrada por el personal de punto de venta cuando no hay buñuelos fritos disponibles. | Indica pérdida de oportunidad por fallos operativos o subestimación de la demanda. |
| **Buñuelos Preparados** | Cantidad total de unidades fritas puestas a disposición del público en un día $T$. | Es el límite físico de la venta. No puede venderse más de lo que se prepara. |
| **Mermas (Desperdicios)** | Unidades fritas que no se vendieron al cierre del día y deben ser desechadas (Vida útil = 1 día). | Representa ineficiencia por sobreestimar la demanda o mala rotación. |
| **Unidades Bonificadas** | Buñuelos entregados sin costo como parte de promociones (ej: el "+1" del 2x1). | Afectan el volumen de salida pero no el ingreso bruto. Vital para el cálculo de costos. |
| **Libras Recibidas** | Materia prima recibida en punto de venta (Harina + Queso + Huevos) en unidades de masa. | Se usa para validar el rendimiento operativo (Yield): **1 lb = 50 buñuelos**. |

## 📅 2. Conceptos Temporales y Triggers

| Término | Definición / Regla | Impacto Esperado |
| :--- | :--- | :--- |
| **Efecto Quincena** | Días 15-16 y 30-31 de cada mes calendario. | Incremento de demanda por mayor liquidez de los clientes. |
| **Prima Legal** | Periodos del 15 al 20 de Junio y del 15 al 20 de Diciembre. | Picos de demanda extraordinarios por ingresos adicionales de ley en Colombia. |
| **Día Festivo** | Cualquier día feriado oficial en Colombia. | **Regla:** Se trata estadísticamente como un **Sábado** (mayor a un viernes, menor a un domingo). |
| **Flag de Pandemia** | Periodo entre 01/05/2020 y 30/04/2021. | Anomalía histórica que debe ser aislada para no sesgar el aprendizaje del modelo. |

## ⛈️ 3. Factores Exógenos (Clima y Macro)

| Término | Definición | Efecto en Buñuelitos |
| :--- | :--- | :--- |
| **Lluvia Ligera** | Precipitación detectable pero que no impide la movilidad. | **Positivo**: Incrementa el "antojo" y el tráfico en puntos de venta. |
| **Lluvia Fuerte** | Precipitación intensa o tormentas que restringen la movilidad. | **Negativo**: Reduce drásticamente el flujo de clientes hacia el local. |
| **Inflación (IPC)** | Índice de Precios al Consumidor mensual. | Afecta el poder adquisitivo del cliente y el costo del Kit de materia prima. |
| **TRM** | Tasa Representativa del Mercado (Dólar). | Impacta indirectamente el costo de insumos importados o maquinaria. |

## 📢 4. Glosario de Marketing y ADS

| Término | Definición | Comportamiento |
| :--- | :--- | :--- |
| **Ventana 2x1** | Periodos Abril-Mayo y Septiembre-Octubre. | Duplicación esperada del volumen de salida (mezcla de pagas y bonificadas). |
| **Ads Activos** | Flag que indica si hay pauta en Facebook/Instagram ese día. | Se activa 20 días antes de la promoción y se apaga el día 25 del segundo mes. |

---
*Este documento es propiedad de Sabbia Solutions & Services (Triple S) y Cafeteria SAS. Actualizado: 2026-03-01.*
