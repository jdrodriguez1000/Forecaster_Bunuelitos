# Project Charter: Proyecto Buñuelitos

## 1. 📝 Información General
*   **Nombre del Proyecto:** Forecaster Buñuelitos
*   **Cliente:** Cafeteria SAS
*   **Proveedor:** Sabbia Solutions & Services SAS (Triple S)
*   **Fecha de Inicio:** 2026-02-28
*   **Estado:** Iniciación

## 2. 🎯 Visión y Objetivos
Desarrollar una solución avanzada de forecasting que permita predecir la demanda real de buñuelos con un horizonte de 6 meses, transformando el proceso empírico actual en un sistema basado en datos (Data-Driven) que minimice sesgos humanos y optimice la gestión de inventarios.

### Objetivos Específicos:
1.  Generar pronósticos mensuales precisos para un horizonte de 6 meses (Mes $X$ a $X+5$).
2.  Reducir el error actual (desfase del 25%) mediante modelos estadísticos y de Machine Learning.
3.  Proporcionar una base científica para la toma de decisiones, disminuyendo la influencia política/gerencial en las proyecciones.
4.  Optimizar los niveles de inventario (evitar agotados y excesos de stock).

## 3. ⚠️ Definición del Problema
Actualmente, el proceso de pronóstico en **Cafeteria SAS** presenta las siguientes debilidades:
*   **Alta Variabilidad:** Errores de hasta el 25% entre la demanda real y la planeada.
*   **Sesgo Humano:** Los pronósticos son influenciados por jerarquías comerciales y financieras, alejándose del comportamiento real del mercado.
*   **Falta de Estándar:** No existe un criterio técnico único; se utilizan métodos inconsistentes (mirar el mes anterior, metas impuestas, etc.).
*   **Impacto Operativo:** Ineficiencia en la cadena de suministro manifestada en rotura de stock o sobrecostos por exceso de inventario.

## 4. 👥 Stakeholders (Interesados)
*   **Cafeteria SAS:** Cliente Final (Áreas de Producción, Ventas y Finanzas).
*   **Gerencia General/Comercial/Operaciones/Financiera:** Tomadores de decisión y fuentes de requerimientos.
*   **Sabbia Solutions & Services (Triple S):** Equipo ejecutor y experto técnico.

## 5. 🧠 Reglas de Negocio y Estacionalidad (Factores Clave)
El modelo debe capturar los siguientes disparadores (`Triggers`) de demanda identificados por los expertos de Cafeteria SAS:

### A. Dinámicas del Calendario (Días Pico)
*   **Jerarquía de Ventas:** Domingo > Sábado > Viernes.
*   **Festivos:** Deben tratarse estadísticamente como **Sábados**.

### B. Efectos de Ingresos (Liquidez)
*   **Efecto Quincena:** Incremento de ventas los días **15-16** y **30-31** de cada mes.
*   **Primas Legales (Colombia):** Ventanas de alta demanda del **15 al 20** de Junio y del **15 al 20** de Diciembre.

### C. Festividades y Eventos Especiales (Niveles de Domingo)
Se identifican periodos donde la venta escala a niveles de un Domingo:
*   **Novenas Navideñas:** 16 al 26 de diciembre.
*   **Semana Santa:** Jueves y Viernes Santos.
*   **Feria de las Flores:** 1 al 10 de agosto (Impacto regional crítico).

### D. Estacionalidad Mensual
*   **Meses Prime:** Diciembre (Líder), seguido de Enero, Junio y Julio.

### E. Anomalías Históricas
*   **Periodo de Pandemia:** Caída crítica de ventas entre el **1 de mayo de 2020 y el 31 de abril de 2021**. Este periodo debe ser tratado como una anomalía estadística (Flag de Pandemia).
*   **Periodo de Recuperación:** Fase de transición post-pandemia hasta finales de 2022.
*   **Estabilidad Post-2023:** Las ventas alcanzan niveles de operación normales y aceptables a partir de enero de 2023.

### F. Variables Exógenas y Factores Externos (Análisis Exploratorio)
*   **Influencia del Clima:**
    *   **Lluvia Ligera:** Posible correlación con un *incremento* en ventas (Efecto "antojo").
    *   **Lluvia Fuerte:** Posible correlación con una *disminución* en ventas (Efecto "movilidad restringida").
*   **Indicadores Macroeconómicos:** Se deben evaluar las siguientes variables para determinar su significancia estadística:
    *   Ajuste del Salario Mínimo (Enero).
    *   Fluctuaciones de la TRM.
    *   Inflación (IPC).
    *   Tasa de Desempleo Colombia.

### G. Estrategia de Marketing y Promociones (Desde 2022)
*   **Promoción 2x1 (Anual):** Se realizan dos ventanas de promoción masiva (Paga 1, Lleva 2):
    *   **Ventana 1:** 1 de Abril al 31 de Mayo.
    *   **Ventana 2:** 1 de Septiembre al 31 de Octubre.
*   **Pauta en Redes Sociales (Facebook e Instagram):**
    *   **Activación:** Inicia aproximadamente **20 días antes** del comienzo de la promoción.
    *   **Cierre (Apagado):** Se desactiva el **día 25** del segundo mes de la promoción (Mayo o Octubre).
    *   **Impacto Esperado:** Incremento significativo en el volumen de unidades, lo que requiere un tratamiento especial en el modelo para no sesgar la demanda "orgánica".

### H. Gestión de Inventario y Operativa
El modelo debe considerar la logística de suministro para optimizar la cadena de valor:
*   **Ciclos de Reabastecimiento de Materia Prima (Kit: Harina, Queso, Huevos):**
    *   **Ciclo 1:** Pedido el día 15 → Entrega el último día del mes anterior (Cubre del 1 al 14).
    *   **Ciclo 2:** Pedido el día 1 → Entrega el día 14 (Cubre del 15 al fin de mes).
    *   **Conversión:** 1 lb de Kit = 50 Buñuelos.
*   **Dinámica de Producto Terminado (Frito):**
    *   **Vida Útil:** 1 día (Perecedero inmediato).
    *   **Venta Real:** `min(Preparados, Demanda Total)`.
    *   **Desperdicio (Merma):** Buñuelos fritos no vendidos al cierre (Pérdida total).
    *   **Agotados:** Demanda no satisfecha por falta de producto frito, incluso si hay materia prima disponible.

## 6. �️ Arquitectura de Datos (Supabase)
El proyecto se conecta a una instancia de Supabase con 6 tablas principales. A continuación se detallan las fuentes identificadas:

### A. Tabla: `ventas`
Contiene la trazabilidad comercial diaria.
*   **Campos clave:** `fecha`, `unidades_totales`, `unidades_pagas`, `unidades_bonificadas`, `es_promocion`, `ads_activos`.

### B. Tabla: `inventario`
Contiene la trazabilidad operativa, mermas y agotados.
*   **Campos clave:** `fecha`, `kit_inicial_bodega`, `kit_recibido`, `lbs_recibidas`, `demanda_teorica_total`, `buñuelos_preparados`, `ventas_reales_totales`, `ventas_reales_pagas`, `ventas_reales_bonificadas`, `buñuelos_desperdiciados`, `unidades_agotadas`, `kit_final_bodega`.

### C. Tabla: `finanzas`
Contiene la trazabilidad de precios, costos y rentabilidad.
*   **Campos clave:** `fecha`, `precio_unitario`, `costo_unitario`, `margen_bruto`, `porcentaje_margen`.

### D. Tabla: `marketing`
Contiene la inversión publicitaria y el performance de pauta.
*   **Campos clave:** `fecha`, `inversion_total`, `ig_cost`, `fb_cost`, `ig_pct`, `fb_pct`, `campaña_activa`.

### E. Tabla: `macroeconomia`
Contiene los indicadores macroeconómicos de Colombia.
*   **Campos clave:** `fecha`, `smlv`, `inflacion_mensual_ipc`, `tasa_desempleo`, `trm`.

### F. Tabla: `clima`
Contiene variables meteorológicas y eventos ambientales.
*   **Campos clave:** `fecha`, `temperatura_media`, `probabilidad_lluvia`, `precipitacion_mm`, `tipo_lluvia`, `evento_macro`, `es_dia_lluvioso`.

### G. Frecuencia de Actualización
*   **Actualización:** Diaria.
*   **Horario:** 01:00 AM (UTC-5).
*   **Alcance:** El dataset real de ayer ($T-1$) se procesa hoy para estar disponible en la orquestación.

### H. Variable Objetivo (Target)
*   **Variable:** `demanda_teorica_total` (Tabla `inventario`).
*   **Justificación:** Representa la demanda real insatisfecha (`ventas_reales_totales + unidades_agotadas`). Este es el valor que el negocio necesita predecir para garantizar la disponibilidad de producto.

## 7. 🛠️ Alcance y Especificaciones Técnicas
Para garantizar la precisión y robustez del sistema, se definen los siguientes lineamientos:

### A. Estrategia de Modelado
*   **Librería Principal:** `skforecast`.
*   **Estrategia:** `ForecasterDirect`.
*   **Modelos Autorizados:** `Ridge`, `RandomForestRegressor`, `LGBMRegressor`, `XGBRegressor`, `GradientBoostingRegressor` y `HistGradientBoostingRegressor`.

### B. Horizonte y Granularidad
*   **Preferencia Operativa:** El modelo pronosticará de forma **diaria** para capturar los efectos de quincena, pauta y festivos detallados anteriormente.
*   **Horizonte de Pronóstico:** **185 días** (equivalente a un poco más de 6 meses).
*   **Agregación Final:** El resultado diario se agrupará mensualmente para la toma de decisiones gerenciales.
*   **Gestión de Salida:** Se reportará el mes actual + los 5 meses siguientes. Los días sobrantes que inicien un séptimo mes serán descartados para evitar incertidumbre por datos parciales.

### C. Regla de Oro (Anti-Data Leakage)
*   **Cierre de Información:** El entrenamiento y la generación del pronóstico deben detenerse estrictamente en el cierre del día **$X-1$** (Ayer).
*   **Restricción:** Queda prohibido el uso de información del día **$X$** (Hoy), ya que se considera incompleta y puede sesgar el resultado.

### D. Metodología de Desarrollo
*   **Enfoque First-Prod:** Desarrollo prioritario en scripts de producción (`src/`). El uso de Notebooks es opcional y se reserva solo para exploraciones puntuales si es necesario.
*   **Validación:** Uso de Backtesting temporal para asegurar que el modelo campeón supere al baseline histórico.

## 8. � Capacidades de Simulación (Análisis What-If)
El sistema permitirá realizar proyecciones alternativas mediante la manipulación de variables exógenas para responder a preguntas estratégicas:

*   **Escenarios de Precio:** ¿Qué sucede con la demanda si aumentamos o disminuimos el `precio_unitario` en un $X\%$?
*   **Dinámica de Promociones:**
    *   **Extensión/Reducción:** Impacto de alargar o acortar la promoción 2x1 en 5, 10 o $N$ días.
    *   **Pauta:** Alteración en la ventana de activación de anuncios en redes sociales.
*   **Sensibilidad Macroeconómica:**
    *   Incremento sostenido de la **Inflación (IPC)**.
    *   Variaciones del **SMLV**: Crecimiento por encima o por debajo de la inflación anual.
*   **Eventos Climáticos:** Simulación de una semana de lluvias intensas (`tipo_lluvia = Fuerte`) y sus efectos en el tráfico de clientes.

## 9. �🏆 Criterios de Éxito
El proyecto se considerará exitoso bajo el cumplimiento de los siguientes hitos:

1.  **Excelencia Predictiva:** El modelo seleccionado debe superar consistentemente a los baselines en métricas de error (MAE, MAPE, RMSE). Se establece como meta mandatoria un **MAPE inferior al 12%** en el set de validación.
2.  **Adopción Institucional:** La herramienta de pronóstico debe ser adoptada por el **comité de expertos** de Cafeteria SAS como el insumo principal y confiable para sus proyecciones de demanda.
3.  **Utilidad Estratégica:** Las simulaciones "What-If" proporcionan insights accionables que permiten a la gerencia anticiparse a cambios en el mercado.

---
*Este documento es la autoridad técnica para el proyecto Buñuelitos y se actualizará según se descubran nuevos insights.*
