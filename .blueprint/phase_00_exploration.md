# Blueprint: Phase 00 - Exploración Inicial & Framework de Gobernanza 2.0 (La Verdad Única)

**Proyecto:** Forecaster Buñuelitos
**Estado:** Fase 00 - Reingeniería v2.0 (Certificada)
**Responsable:** Data Health Auditor (Antigravity)

---

## 1. 🎯 Propósito Estratégico
Evolucionar el **Contrato de Datos** de un simple "checklist" a un **Marco de Gobernanza Industrial**. Este blueprint define las leyes inmutables que blindan la integridad de los datos de Cafetería SAS, asegurando que cada predicción de demanda se base en una realidad completa, coherente y estadísticamente estable (Cinturón de Seguridad v2.0).

---

## 🏛️ 2. Arquitectura de Gobernanza (Los 4 Pilares de la Verdad)

El sistema de validación organiza las 16 reglas maestras del proyecto en cuatro dimensiones críticas de inspección:

### 🧩 Pilar 1: Integridad Estructural (El Esqueleto)
*Garantiza que el formato y el contenedor de los datos sean procesables.*
*   **Identidad**: Validación de nombres de archivos y columnas (Puntos 1 y 2).
*   **Completitud**: Presencia obligatoria de todas las columnas requeridas (Punto 3).
*   **Esquema**: Certificación de tipos de datos técnicos (int, float, string, datetime) (Punto 4).
*   **Higiene**: Control de nulos, valores centinelas y duplicados (Puntos 9.1 a 9.4).

### 🥁 Pilar 2: Integridad de Proceso (El Ritmo)
*Asegura que la "película" de los datos fluya sin saltos ni contaminaciones.*
*   **Sincronización (Masa vs Tiempo)**: Validación de brecha de días (5.1) cruzada con el volumen de registros recibidos (5.2) para detectar sub-reportes.
*   **Continuidad**: Detección de huecos temporales (gaps) en la serie (Punto 6).
*   **Seguridad**: Bloqueo de fuga de futuro (Data Leakage) (Punto 7).
*   **Conectividad**: Integridad referencial y validación cruzada entre tablas (Punto 8).

### 🧠 Pilar 3: Salud Estadística (La Personalidad)
*Mide la estabilidad y el comportamiento de los valores reales.*
*   **Perfilamiento Profundo**: Cálculo de media, mediana, desviación, percentiles y rango (Punto 10.1).
*   **Densidad de Señal**: Identificación de alta cardinalidad, cero varianza y peso de ceros (10.2 a 10.4).
*   **Anomalías**: Detección de valores atípicos (outliers) fuera de límites lógicos (Punto 10.5).
*   **Estabilidad (Drift)**: Monitoreo de desvíos técnicos en toda la historia (10.6) y específicamente en el horizonte del proyecto (10.7).

### ⚖️ Pilar 4: Lógica de Dominio y Gobernanza (Las Leyes)
*Traduce el conocimiento del negocio en sentencias de ejecución.*
*   **Leyes de Negocio**: Validación de consistencia interna por archivo y entre tablas (Puntos 14.1 y 14.2).
*   **Métricas Operativas**: Perfilamiento de datos tipo objeto, booleanos y fechas (Puntos 11, 12 y 13).
*   **Protocolo de Decisión**: Clasificación final de la ejecución (SUCCESS, WARNING, FAILURE) (Puntos 15 y 16).

---

## 🚦 3. Protocolo de Sentencia y Umbrales (Severity Levels)

La ejecución del pipeline depende del estado final del contrato:

1.  **🟢 SUCCESS**: Todas las pruebas superadas o desviaciones de Drift < 12%. El sistema procede al modelado.
2.  **🟡 WARNING**: Al menos un aviso preventivo o desviaciones > 12%. Se informa con mensaje de precaución, pero se permite avanzar. Umbral fijado en **12%** por defecto, pero parametrizable por variable.
3.  **🔴 FAILURE**: Violación de cualquier regla de los **Pilares 1 y 2**, o de Reglas de Negocio Críticas del **Pilar 4**. El sistema realiza un **Hard Stop** inmediato.

---

## 🔐 4. Gobernanza en Supabase (Transparencia Total)
Para garantizar la "Última Verdad" en la plataforma:
*   **Contrato Activo**: Solo un registro en la tabla `data_contracts` tendrá `is_active = True`. La vista de Supabase filtrará exclusivamente por este flag.
*   **Trazabilidad**: Las versiones anteriores (v1.x) se conservan en el historial inmutable (`history/`) vinculadas a su `contract_id` para auditoría, pero pierden su estado activo al registrarse la v2.0.

---

## 📅 5. Roadmap Actualizado (Changelog v2.0)
*   **[2026-03-01]**: Implementación inicial del Framework de 3 capas (v1.x). (Finalizado).
*   **[2026-03-02]**: **REINGENIERÍA v2.0**: Migración masiva a la arquitectura de **4 Pilares de la Verdad**.
*   **[2026-03-02]**: Incorporación de la regla de **Suficiencia de Masa** (Volumen vs Tiempo).
*   **[2026-03-02]**: Definición de umbrales parametrizables (**12%**) y jerarquía de fallo para Reglas de Negocio.
*   **[2026-03-02]**: **HITO ALCANZADO**: Consolidación del Plan Maestro de Gobernanza 2.0 en un único documento de Fase 00.

---

> [!IMPORTANT]
> Esta reingeniería trasciende el código; es un compromiso con la calidad de las decisiones de Cafetería SAS. Ningún buñuelo será pronosticado sin pasar primero por este filtro de integridad de 4 pilares.
