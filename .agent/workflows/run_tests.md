---
description: Pipeline de Aseguramiento de Calidad - Ejecución de Pruebas Unitarias e Integración (Inteligente)
---

// turbo-all
1. Configurar el entorno de Python:
```powershell
$env:PYTHONPATH='.'
```

2. Ejecutar la Orquestación de Calidad Global:
```powershell
# Este script detecta automáticamente si hay pruebas de integración para ejecutarlas.
# Incluye el protocolo de Dual Persistencia (latest.json + history/)
python scripts/qa_orchestrator.py
```

> [!TIP]
> Use este workflow después de cualquier modificación en `src/` o en el contrato de datos. El sistema es inteligente: si detecta pruebas de integración las ejecutará; de lo contrario, solo certificará las pruebas unitarias.
>
> [!IMPORTANT]
> Las pruebas relacionadas con la **Fase Explorer (Phase 00)** están excluidas de este flujo de trabajo para mantener el rigor productivo de las fases subsiguientes.

---

## 🚦 Salida Esperada
Certificación completa de la fase actual con reportes inmutables en `tests/reports/`.
