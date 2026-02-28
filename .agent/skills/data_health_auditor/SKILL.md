---
name: data_health_auditor
description: Actúa como el Data Steward del proyecto, validando la integridad, frescura y consistencia de las fuentes de datos (Supabase) contra un Contrato de Datos antes de permitir la ejecución del pipeline.
---

# Skill: Auditoría de Salud y Contrato de Datos (Forecaster Buñuelitos)

Esta habilidad es el primer filtro de seguridad del sistema. Su misión es garantizar que los datos de entrada sean técnicamente aptos y lógicamente coherentes para el modelado, evitando "basura adentro, basura afuera" (GIGO).

## 📝 1. El concepto del "Contrato de Datos" (Data Contract)
El Contrato de Datos es la verdad única sobre cómo deben verse los datos. Se define en `config.yaml` y esta habilidad lo audita bajo cuatro dimensiones:

*   **Estructural (Schema):** Nombre de columnas, tipos de datos (float, int, datetime) y claves primarias.
*   **De Frescura (Freshness):** ¿Cuándo fue la última actualización? (Cumplimiento de la regla $T-1$).
*   **De Completitud (Completeness):** Porcentaje máximo de nulos permitido por columna (especialmente en el target `demanda_teorica_total`).
*   **De Rango (Validity):** Límites lógicos (ej: precios > 0, ventas >= 0, probabilidad_lluvia entre 0 y 1).

## 🚀 2. Protocolo de Auditoría por Fase (Fase 00)
Antes de iniciar cualquier fase de orquestación, se debe ejecutar la validación:

1.  **Carga del Contrato:** Leer las expectativas desde `config.yaml` de la sección `extractions` y `preprocessing`.
2.  **Validación Exhaustiva:**
    *   **Test de Tipos:** Verificar que las fechas sean objetos `datetime` y las cantidades sean numéricas.
    *   **Test de Continuidad:** Detectar si hay "saltos" en la serie de tiempo antes de la reindexación.
    *   **Test de Duplicados:** Identificar registros que violan la unicidad de la fecha.
3.  **Gestión de Errores (Stop-Go Logic):**
    *   **Hard Failure (Errores Críticos):** Columnas faltantes o nulos en el target. Detiene el pipeline inmediatamente.
    *   **Soft Warning (Advertencias):** Nulos en variables exógenas opcionales. El pipeline continúa pero genera una alerta en el reporte.

## 📊 3. Reporte de Salud de Datos (Data Health Report)
Toda auditoría genera un artefacto oficial en `outputs/reports/phase_00_data_audit_latest.json` que incluye:
*   `health_score`: Un índice de 0 a 100 de la salud del dataset.
*   `violations`: Lista detallada de campos que no cumplieron el contrato.
*   `freshness_status`: Fecha del dato más reciente encontrado vs fecha esperada.

## 🛠️ 4. Integración con MLOps (First-Prod)
*   **Prevención de Regresión:** La habilidad debe detectar si un nuevo despliegue de base de datos ha roto la compatibilidad con el código de `src/loader.py`.
*   **Auditoría de Mocking:** En entornos de test, valida que los datos simulados también cumplan el contrato para evitar pruebas con datos falsos poco realistas.

## ⚖️ 5. Reglas de Resiliencia específicas para Buñuelitos
*   **Target Guard:** El campo `demanda_teorica_total` no puede tener un MAPE de nulos superior al definido en la configuración (usualmente 0% antes de imputación).
*   **Event Guard:** Validar que los flags de eventos especiales (Pandemia, Feria de las Flores) existan en el rango de fechas consultado.
