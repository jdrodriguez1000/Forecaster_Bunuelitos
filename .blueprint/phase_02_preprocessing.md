# Blueprint: Phase 02 - Preprocessing (El Sanador / The Healer)

**Proyecto:** Forecaster Buñuelitos
**Estado:** En Desarrollo (Fase de Diseño Técnico)
**Responsable:** Pipeline Forecasting Manager (Antigravity)

---

## 1. 🎯 Propósito Estratégico
El objetivo de la Fase 02 es transformar los datos crudos auditados en la Fase 01 en un **Dataset Maestro de Entrenamiento** que sea físicamente coherente y libre de ruidos operativos. Actúa como "El Sanador", resolviendo inconsistencias de inventario, errores de registro and vacíos de información mediante lógica de negocio avanzada (Healing Algorithms).

## 2. 🏗️ Arquitectura del Componente (Preprocessor Engine)

El `Preprocessor` está diseñado como un motor de ejecución secuencial basado en el archivo `config.yaml`, compuesto por cuatro capas de blindaje:

### 2.0. Capa 0: Orquestación y Handshake (Go/No-Go)
Antes de tocar cualquier dato, el motor realiza las siguientes validaciones de seguridad:
- **Handshake con Supabase:** Consulta obligatoria a `data_inventory_status`. Si alguna de las 6 tablas tiene un estado de `FAILURE` o un `health_score < 0.90`, el proceso se detiene automáticamente para evitar contaminar la historia.
- **Detección de Delta (Incremental):** Comparación entre `data/01_raw` y el archivo maestro en `data/02_cleansed`. El sistema identifica la brecha temporal para procesar solo los nuevos registros.
- **Inyección de Semilla ($T-1$):** Para garantizar la continuidad de leyes físicas (como el stock), el motor extrae el último día del set ya sanado para usarlo como referencia del estado inicial del nuevo lote.

### 2.1. Capa 1: Política Maestra de Outliers (Context-Aware)
Antes de reconstruir, el sistema evalúa los valores extremos:
- **Validación Contextual:** Cruce automático con calendarios de promociones, festivos y pauta digital.
- **Diferenciación:**
    - **Business Success (`flag_outlier = 1`):** Valores altos explicados por el negocio se conservan.
    - **Data Error (`flag_outlier = 0`):** Valores inexplicables se convierten en `NaN` para ser sanados por los algoritmos de tabla.

### 2.2. Capa 2: Algoritmos de Reconstrucción (Sequential Healing)
Ejecución de pasos lógicos definidos en `config.yaml` por cada dominio:
- **Ventas (Baile de Sanación):** Reconstrucción de la simetría 2x1 (Pagas vs Bonificadas).
- **Clima (Inercia Ambiental):** Imputación por arrastre térmico y consistencia de banderas de lluvia.
- **Finanzas (Estabilidad Contractual):** Herencia de precios y costos con recálculo forzado de márgenes.
- **Marketing (Atribución de Pauta):** Reconstrucción de costos por canal y sincronización de flags de campaña.
- **Inventario (Balance de Masa 2.0):** El núcleo de la fase, diseñado para armonizar la física de la producción.

### 2.3. Capa 3: Consolidación y Certificación (The Quality Gate)
Fusión de todas las tablas en un único objeto maestro asegurando:
- **Continuidad Cronológica:** Relleno de días faltantes para crear una serie de tiempo ininterrumpida.
- **4 Pilares de Tranquilidad:** Higiene Total (0 nulos), Unicidad Temporal, Continuidad y Cierre de Masa.

### 2.4. Capa 4: Cierre de Fase y Trazabilidad (Control Plane Sync)
Como último paso, el sistema sincroniza el resultado con Supabase:
- **Reporting en Nube:** Registro en la tabla `pipeline_execution_status`.
- **Métricas de Éxito:** Almacenamiento de `master_row_count`, `health_score_avg` y el conteo de `anomalies_detected` (outliers y nulos curados).
- **Puntero de Verdad:** Registro del `output_path` oficial para que la Fase 03 (Features) sepa de dónde leer.

---

## 🔬 3. Lógica Destacada: Balance de Masa 2.0
Para resolver los fallos de rendimiento y stock detectados en la auditoría, se aplica una **Reversa Operativa**:
1.  **Ley del Cierre Nocturno:** El stock inicial de hoy se fuerza a ser igual al final de ayer (`Always Condition`).
2.  **Techo de Vitrina:** La producción se eleva automáticamente si es menor a las ventas registradas.
3.  **Contabilidad Inversa:** El `kit_final_bodega` se recalcula basándose en un rendimiento fijo de **1 lb = 50 buñuelos**, asegurando que la harina consumida coincida con la producción final.

---

## � 4. Entregables y Salidas
- **`data/02_cleansed/master_cleansed.parquet`**: El insumo final certificado.
- **`outputs/reports/phase_02/`**: Detalle técnico de sanaciones y reporte de calidad.
- **Supabase (`pipeline_execution_status`)**: Registro de auditoría del Control Plane.

---

## 🛠️ 5. Changelog & Justificación Técnica
- **[2026-03-03]**: Diseño del algoritmo de **Balance de Masa 2.0** para resolver inconsistencias de Kits vs Libras.
- **[2026-03-03]**: Integración de la **Ley del Cierre Nocturno** y la **Ley de Disponibilidad Física**.
- **[2026-03-03]**: **Control Plane Sync**: Implementación de la tabla `pipeline_execution_status` para trazabilidad total del éxito/fallo de la fase y métricas de salud promedio.
- **[2026-03-03]**: **Lógica Delta**: Adición del proceso de "Handshake" y procesamiento incremental para eficiencia operativa.
