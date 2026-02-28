---
name: quality_assurance_manager
description: Automatiza la creación y ejecución de pruebas de software y ciencia de datos, garantizando la integridad de los resultados y la detección temprana de anomalías en flujos positivos y negativos.
---

# Skill: Gestor de Calidad y QA (Forecaster Buñuelitos)

Esta habilidad es la responsable de garantizar la robustez técnica y la validez lógia del proyecto. Se encarga de diseñar, generar y supervisar las pruebas que blindan el sistema contra errores de programación, fallos de datos y, sobre todo, contra el sesgo o la fuga de información (Data Leakage).

## 🎯 1. Estrategia de Flujos Positivos (Happy Path)
Asegura que el sistema funcione correctamente cuando los datos son perfectos y cumplen el contrato.

*   **Integridad de la Serie**: Validar que tras el preprocesamiento no existan huecos temporales y la frecuencia sea estrictamente diaria.
*   **Cálculo de Demanda**: Verificar que `demanda_teorica_total` sea la suma correcta de ventas y agotados según la lógica de negocio.
*   **Comportamiento de Festivos**: Confirmar que los días marcados como festivos en el calendario sean tratados estadísticamente como Sábados.
*   **Horizonte de Predicción**: Validar que el modelo genere exactamente los 185 días requeridos sin interrupciones.

## ⚠️ 2. Estrategia de Flujos Negativos y Resiliencia
Asegura que el sistema falle con elegancia o corrija anomalías cuando los datos son imperfectos.

*   **Manejo de Gaps**: Inyectar ausencias de registros para fechas aleatorias y verificar que el preprocesador cree las filas con `NaN` (Reindexación).
*   **Tratamiento de Duplicados**: Proveer intencionalmente filas duplicadas para la misma fecha y validar que se conserve únicamente la **última actualización**.
*   **Datos Corruptos o Outliers**: Introducir valores de ventas negativos o absurdamente altos para validar que los filtros de limpieza o las imputaciones lógicas los gestionen.
*   **Falla de Conexión**: Simular errores de acceso a Supabase para verificar que los logs capturen el error y el sistema no colapse sin información.
*   **Configuración Errónea**: Cambiar parámetros críticos en `config.yaml` (ej. rutas inexistentes o hiperparámetros inválidos) y validar que los tests de unidad detecten la inconsistencia.

## 🛡️ 3. Blindaje de Ciencia de Datos (Temporality & Leakage)
Pruebas específicas para el dominio de series de tiempo.

*   **Anti-Data Leakage**: Intentar entrenar el modelo incluyendo variables del día $T$ para predecir $T$ y asegurar que el validador lance una excepción o falle el test.
*   **Estacionaridad y Lags**: Validar que los rezagos (lags) generados no contengan información futura (desplazamiento correcto).
*   **Validación Cruzada Temporal**: Verificar que los cortes de entrenamiento/prueba respeten estrictamente la cronología.

## 🛠️ 4. Protocolos de Implementación (Pytest & Mocks)
*   **Aislamiento Total (Mocking)**: Uso obligatorio de herencias de `unittest.mock` para simular la base de datos. Está estrictamente prohibido que un test escriba en tablas reales o lea de ellas sin un flag explícito de integración.
*   **Fixtures Reutilizables**: Creación de sets de datos "semilla" (Gold Standard) en `conftest.py` para que todos los tests partan de la misma base conocida.
*   **Estructura AAA**: Seguir siempre el patrón *Arrange* (Preparar), *Act* (Ejecutar), *Assert* (Verificar).

## 📊 5. Trazabilidad y Reportes
*   **Dual Persistencia**: Todo resultado de ejecución de pruebas se guarda en `tests/reports/` tanto en versión `latest.json` como en el historial con timestamp.
*   **Métricas de QA**: Los reportes deben incluir porcentaje de cobertura, tiempo de ejecución y desglose de fallos por tipo (Unidad vs Integración).
