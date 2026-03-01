---
description: Pipeline de Aseguramiento de Calidad - Ejecución de Pruebas Unitarias
---

// turbo-all
1. Configurar el entorno de Python:
```powershell
$env:PYTHONPATH='.'
```

2. Ejecutar la suite de pruebas industrializada:
```powershell
# Este script incluye el protocolo de Dual Persistencia (latest.json + history/)
python scripts/run_unit_tests.py
```

3. (Opcional) Generar reporte de cobertura:
```powershell
pytest tests/unit/ --cov=src --cov-report=term-missing
```

> [!TIP]
> Use este workflow después de cualquier modificación en `src/utils/` o en el `data_contract_latest.yaml` para asegurar que las reglas de negocio sigan operando correctamente.
