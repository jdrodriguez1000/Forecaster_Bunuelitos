# Blueprint: Phase 00 - Exploración Inicial & Framework de Gobernanza

**Proyecto:** Forecaster Buñuelitos
**Estado:** Fase 00 Completada (Certificada)
**Responsable:** Data Health Auditor (Antigravity)

---

## 1. 🎯 Propósito Estratégico
Establecer el **Contrato de Datos** como el "Cinturón de Seguridad" del sistema. Esta fase no solo explora los datos, sino que define las leyes inmutables que deben cumplirse en cada ejecución del pipeline para asegurar la integridad de los pronósticos de Cafeteria SAS.

## 2. 🏛️ Arquitectura del Contrato (Las 3 Capas)

El sistema de gobernanza se divide en tres niveles de persistencia y verdad:

### Layer 1: El Manual de Normas (Archivo YAML)
Es el archivo de configuración maestro, humano-legible y editable por el equipo de Triple S.
- **Ruta:** `schemas/contract/data_contract_latest.yaml`
- **Contenido:**
  - **Estructura:** Definición de nombres de columnas y tipos de datos (int, float, string, datetime).
  - **Reglas de Negocio:** Categorías permitidas y rangos lógicos.
  - **Metadatos:** Versión del contrato y `contract_id`.
- **Doble Persistencia:** Mantiene un historial inmutable en `schemas/contract/history/`.

### Layer 2: La Foto del Pasado (Archivo JSON - Snapshot)
Captura el estado estadístico exacto de los datos durante la fase de exploración.
- **Ruta:** `schemas/statistical/initial_statistical_snapshot.json`
- **Contenido:**
  - **Estadística Descriptiva:** Media, desviación estándar, cuantiles y mapa de nulos.
  - **Outliers & Drift:** Umbrales de referencia para validaciones dinámicas.
- **Doble Persistencia:** Mantiene un historial inmutable en `schemas/statistical/history/`.
- **Enlace:** Vinculado internamente al `contract_id` del contrato YAML correspondiente.

### Layer 3: El Cerebro Operativo (Base de Datos Supabase)
Persistencia para la orquestación y auditoría histórica.
- **Tabla `data_contracts`:** Registra las versiones de contratos activos, sus rutas físicas y estados.
- **Tabla `validation_logs`:** (Se llena en cada ejecución). Guarda el `id_validacion`, `fecha`, `resultado` y `detalle_error`.
- **Función:** Permite auditoría gerencial y trazabilidad técnica sobre la salud histórica del proyecto.

---

---

### 2.1. Arquitectura de Gobernanza (Estructura de Carpetas)
1.  **Directorio de Contratos:** `schemas/contract/`. Contiene el `data_contract_latest.yaml` y su histórico.
2.  **Directorio Estadístico:** `schemas/statistical/`. Contiene el `initial_statistical_snapshot.json` y su histórico.
3.  **Cerebro Operativo (DB):** Tablas `data_contracts` y `validation_logs` en Supabase para trazabilidad industrial.

---

## 🧼 3. Estándares Globales de Integridad (Safe-Zone)
El sistema aplica un "Escaneo Estructural" previo a cualquier lógica de negocio:

*   **Detección de Centinelas:** Identificación de códigos de error (`-999`, `9999`, `"NULL"`, `"test"`) mapeados por tipo de dato.
*   **Gobernanza de Categorías:** Validación de listas blancas (ej. `La Niña`, `Ligera`). Implementación de mitigación **"Map to Others"** (WARNING) ante nuevos valores.
*   **Unicidad y Nulos:** Bloqueo estricto de duplicados en fechas y tolerancia del 0% en variables críticas (target, ventas).
*   **No Negatividad:** Prohibición en todas las métricas operativas.

---

## 📉 4. Monitoreo Dinámico y Detección de Drift
Para evitar que el pasado lejano sesgue la validación del presente:

*   **Ventana de Referencia (185 Días):** El sistema compara el lote de datos entrante contra los últimos **185 días** (Lookback Period), no contra el promedio plano de 10 años.
*   **Validación por Perfiles de Día:** La comparación se realiza por día de la semana (ej. Domingo vs Promedio Domingo reciente).
*   **Umbrales de Drift:** Si el promedio del lote actual se desvía más de un **15%** de la ventana de referencia, se genera un **WARNING** de "Trend Shift".

---

## 🚦 5. Protocolo de Validación (3 Estados)
Cada regla tiene asignada una severidad:

1.  **🟢 SUCCESS:** 100% de cumplimiento. El pipeline avanza al entrenamiento.
2.  **🟡 WARNING:** Discrepancia no crítica (ej. inconsistencia de marketing, error leve de pesaje, Drift de tendencia). Registro el incidente pero continúo.
3.  **🔴 FAILURE:** Violación crítica (ej. target nulo, margen negativo, duplicados en fechas). El sistema realiza un **Hard Stop** inmediato.

---

## 🎯 6. Interpretación de la Verdad (Ventas vs Inventario)
*   **Sincronía Obligatoria:** `ventas.unidades_totales` == `inventario.demanda_teorica_total`. Esta es la base de la coherencia del modelo.

---

## 📅 7. Roadmap de Ejecución Fase 00
1.  **[CONTRACT]** Finalizar el contrato YAML (v1.3) en `schemas/contract/`. **(COMPLETADO ✅)**
2.  **[CONNECT]** Inicializar `DBConnector` con credenciales de Supabase. **(COMPLETADO ✅)**
3.  **[SNAPSHOT]** Generar el `initial_statistical_snapshot.json` en `schemas/statistical/`. **(COMPLETADO ✅)**
4.  **[AUDIT]** Correr el motor de validación cruzada y generar el reporte final de salud. **(COMPLETADO ✅ - Score: 74.0)**
5.  **[QA-INIT]** Implementación de Suite de Pruebas Unitarias e infraestructura de reportes segregados. **(COMPLETADO ✅)**
6.  **[DEPLOY]** Sincronización con GitHub bajo estándares MLOps. **(COMPLETADO ✅)**

## 🛠️ 7. Changelog & Justificación
- **[2026-03-01]**: Actualización del Blueprint. Implementación del Framework de gobernanza de 3 capas.
- **[2026-03-01]**: Definición de la lógica de balance 50/50 para promociones y reglas de identidad de la variable target.
- **[2026-03-01]**: Incorporación de validaciones cruzadas (Cross-Table Checks) entre Ventas, Inventario y Marketing.
- **[2026-03-01]**: **HITO ALCANZADO**: Implementación de infraestructura de QA Industrializada (`run_unit_tests.py`) con reporte detallado por fases y cobertura (65.45%).
- **[2026-03-01]**: **HITO ALCANZADO**: Ejecución exitosa de auditoría inicial (`explorer.py`) con registro de contrato activo en Supabase.
- **[2026-03-01]**: **HITO ALCANZADO**: Despliegue inicial del repositorio `Forecaster_Bunuelitos` en GitHub con limpieza de artefactos temporales.
