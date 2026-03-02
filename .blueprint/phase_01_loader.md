# Blueprint: Phase 01 - Loader & Auditor (El Portero de Discoteca)

**Proyecto:** Forecaster Buñuelitos
**Estado:** Fase 01 Completada (Certificada)
**Responsable:** Pipeline Forecasting Manager (Antigravity)

---

## 1. 🎯 Propósito Estratégico
Transformar la extracción de datos estática en un proceso dinámico de **Ingeniería de Calidad**. La Fase 01 actúa como el "Portero de Discoteca" del proyecto: ningún dato entra al ecosistema de modelado sin antes ser auditado contra el Contrato de Datos (Fase 00). El objetivo es garantizar que el ruido operativo no contamine la inteligencia del forecasting.

## 2. 🏗️ Arquitectura del Componente (Motor de Carga)

El `DataLoader` es el corazón de esta fase, diseñado bajo principios de **Idempotencia** y **Resiliencia**:

### 2.1. Estrategia de Ingestión Delta (Incremental)
- **Lógica:** El sistema identifica la `fecha_máxima` en el almacenamiento local (`data/01_raw/`) y solo descarga de Supabase los registros posteriores.
- **Deduplicación:** Aplicación de la regla de "Última Verdad" (conservar el registro más reciente en caso de colisión de timestamps).
- **Persistencia Inmutable:** Los datos se guardan en formato **Parquet** para optimizar espacio, preservar tipos de datos y acelerar lecturas futuras.

### 2.2. El Motor de Auditoría (`DataHealthAuditor`)
Cada tabla descargada pasa por un escaneo exhaustivo que incluye:
1.  **Validación de Esquema:** Tipos de datos y presencia de columnas obligatorias.
2.  **Integridad Temporal:** Detección de huecos (gaps) en la serie de tiempo diaria y validación de fronteras (usando `audit_reference_date` para estabilidad en pruebas).
3.  **Leyes de Negocio:** Evaluación de reglas aritméticas y lógicas (ej. `unidades_totales == pagas + bonificadas`) utilizando el `BusinessRulesEngine`.
4.  **Detección de Drift:** Comparación estadística del lote actual contra el Snapshot histórico de la Fase 00.
5.  **Cero Huella Técnica:** Las columnas temporales (`__temp_*`) utilizadas para validaciones se eliminan estrictamente antes de la persistencia y no afectan el cálculo de nulos (`null_pct`).

### 2.3. Sincronización del Panel de Control (Cloud-Local Sync)
Se implementó una capa de persistencia remota en Supabase para asegurar que el **Control Plane** esté siempre alineado con la realidad local:
- **Actualización Incondicional:** Incluso si no hay datos nuevos (`NO_NEW_DATA`), el sistema audita la copia local y actualiza los indicadores de salud (`health_score`) y fechas en la tabla `data_inventory_status`.
- **Trazabilidad Remota:** Cada auditoría genera una entrada en `validation_logs`, permitiendo monitorear la degradación de datos desde cualquier interfaz (Nube o Local).

---

## 🚦 3. Protocolo de Gobernanza y Salida (Quality Gates)

La Phase 01 no permite el avance si no se cumplen los estándares mínimos de salud:

*   **Estado SUCCESS (Score > 90):** Los datos son grabados y el pipeline continúa.
*   **Estado WARNING (Score 70-90):** Los datos se graban, pero se dispara una alerta en el reporte ejecutivo detallando las anomalías (ej. Ruptura leve de stock).
*   **Estado FAILURE (Score < 70):** **Hard Stop**. No se actualizan los archivos locales para evitar contaminar el entrenamiento con datos corruptos.

---

## 📄 4. Protocolo de Reporte (Doble Persistencia)

Cada ejecución genera evidencia auditable en `outputs/reports/phase_01/`:
- **`latest`**: Puntero actual con estructura estandarizada (incluye listas consolidadas de `violations` y `passed_checks` por tabla).
- **`history`**: Registro inmutable con timestamp (`YYYYMMDD_HHMMSS`) para auditoría de degradación de datos en el tiempo.

---

## 🧪 5. Infraestructura de Calidad (Safe-Zone)

Se implementó un **Portero de QA de 3 Niveles** para blindar el código:
1.  **Unit Tests (Motor):** Valida que las funciones individuales (cálculo de nulos, carga de archivos) funcionen correctamente.
2.  **Functional Tests (Misión):** Pruebas de caja negra que simulan escenarios de negocio (ej. "Si llegan ventas negativas, el auditor debe marcar FAILURE").
3.  **Integration Tests (Tubería):** Valida la conexión real con Supabase y la escritura en disco.

**Exclusión Estratégica:** Las pruebas de la Fase 00 (Exploración) han sido segregadas del flujo productivo para mantener el pipeline ágil y enfocado en código certificado.

---

## 📅 6. Roadmap y Logros de Ejecución
1.  **[CORE]** Implementación del `DataLoader` con soporte para múltiples tablas. **(COMPLETADO ✅)**
2.  **[AUDIT]** Integración del `BusinessRulesEngine` para evaluación dinámica de reglas en YAML. **(COMPLETADO ✅)**
3.  **[PERSISTENCE]** Implementación del motor de reportes con Doble Persistencia. **(COMPLETADO ✅)**
4.  **[QA-LEVEL-2]** Creación de la suite de pruebas funcionales para la Fase 01. **(COMPLETADO ✅)**
5.  **[ORCHESTRATE]** Desarrollo del `qa_orchestrator.py` para ejecución inteligente de tests. **(COMPLETADO ✅)**
6.  **[CLEANUP]** Auditoría de salud final y limpieza de artefactos temporales de prueba. **(COMPLETADO ✅)**

## 🛠️ 7. Changelog & Justificación Técnica
- **[2026-03-01]**: Migración de almacenamiento de CSV a **Parquet** para asegurar integridad de tipos (especialmente fechas y booleanos).
- **[2026-03-02]**: Refactorización del QA Orchestrator para manejar codificación UTF-8 en Windows, evitando errores de emojis en logs.
- **[2026-03-02]**: Implementación de la exclusión de pruebas de Fase 00 en el runner oficial para evitar falsos negativos en el pipeline productivo.
- **[2026-03-02]**: **Auditoría Refinada**: Implementación de `audit_reference_date` para pruebas estables y eliminación de columnas `__temp_*` en reportes de nulos.
- **[2026-03-02]**: **Consolidación de Reportes**: Mejora en la estructura JSON del reporte de auditoría para facilitar el consumo por niveles superiores del pipeline.
- **[2026-03-02]**: **HITO ALCANZADO**: Certificación de la Fase 01 con un Score de Salud de **99.0** en ventas y **SUCCESS** global en todas las tablas de Cafetería SAS.
- **[2026-03-02]**: **Sincronización Total**: Refactorización del `DataLoader` para garantizar que la tabla `data_inventory_status` y `validation_logs` en Supabase se actualicen incluso en ausencia de datos nuevos, eliminando discrepancias nube-local.
- **[2026-03-02]**: Despliegue final certificado al repositorio GitHub.
