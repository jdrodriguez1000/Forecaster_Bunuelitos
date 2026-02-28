---
trigger: always_on
---

# Strategic Rules: Forecaster Buñuelitos

Este documento define la dirección estratégica, la identidad corporativa y la gobernanza del proyecto de forecasting para Cafeteria SAS. Es el marco de referencia para la toma de decisiones de alto nivel.

---

## 1. 🎯 Identidad y Visión del Proyecto
*   **Consultora Lider:** Sabbia Solutions & Services SAS (Triple S).
*   **Cliente Final:** Cafeteria SAS.
*   **Propósito:** Proporcionar una ventaja competitiva mediante la predicción precisa de la demanda de "Tu Buñuelito", eliminando la dependencia de la "política de pasillo" y sustituyéndola por decisiones basadas en datos (Data-Driven Decisions).

## 2. 🏆 Métricas de Éxito y Objetivos
*   **Precisión Objetivo:** Mantener un **MAPE < 12%** en el horizonte de validación ciega. Si el error supera este umbral, el sistema debe disparar protocolos de auditoría técnica.
*   **Valor de Negocio:** Disminuir el desperdicio (merma) y minimizar las ventas perdidas (unidades agotadas) mediante un balance óptimo de la producción.

## 3. ⚙️ Metodología First-Prod (Ciclo de Vida)
El proyecto no se basa en prototipos sueltos, sino en un flujo de ingeniería robusto:

1.  **[EXPLORE] Fase 00 - Auditoría de Salud:** Validación del Contrato de Datos directamente en Supabase antes de cualquier cálculo.
2.  **[CONFIG] Fase de Parametrización:** Ningún valor táctico puede vivir en el código. `config.yaml` es el centro de control.
3.  **[CORE] Desarrollo Productivo:** Lógica implementada en módulos `/src/` diseñados para ser escalables.
4.  **[UNIT-TEST] Aseguramiento de Calidad:** Validación obligatoria mediante el `quality_assurance_manager`. No se permite el avance si hay tests fallidos.
5.  **[ORCHESTRATE] Ejecución del Pipeline:** Integración de fases vía `main.py` bajo modos controlados (`load`, `train`, `forecast`).
6.  **[PROD-OUT] Generación de Artefactos:** Producción inmutable de modelos, figuras y reportes con trazabilidad histórica.
7.  **[CLOSE] Cierre de Hito:** Formalización de la fase con documentación oficial y Git Commit.

## 📄 4. Protocolo de Documentación y Gobernanza
Para asegurar la "verdad única", cada fase debe generar:

### 4.1. Blueprint de Fase (Contrato Técnico Evolutivo)
*   **Función:** Es el diseño técnico y funcional del experimento.
*   **Evolución:** Debe actualizarse durante la fase para registrar cada modificación técnica (Changelog) y su justificación. No es un documento estático, es el historial de la evolución del plan.

### 4.2. Informe Ejecutivo (Wow Factor)
*   **Foco:** Comunicación gerencial de alto impacto.
*   **Estructura:** Dividido en "Puntos de Poder" (Logros) y "Verdades Críticas" (Riesgos). Cada punto debe tener evidencia numérica y fuente clara.

## ⚖️ 5. El Gatekeeper (Estrategia de Aprobación)
*   **Regla de Oro:** El sistema no tiene autonomía para pasar de una fase compleja a otra sin intervención humana.
*   **Protocolo:** El usuario (Stakeholder de Triple S) debe leer el Informe Ejecutivo, revisar los indicadores de salud de la fase y dar su aprobación explícita. Esto asegura que la inteligencia de la IA esté siempre alineada con el criterio del experto humano.
