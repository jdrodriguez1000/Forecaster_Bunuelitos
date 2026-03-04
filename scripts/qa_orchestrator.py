import os
import sys
import subprocess
import json
from datetime import datetime

# Configure standard output to handle emojis and special characters on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def run_script(script_path):
    """Runs a python script and returns its success status."""
    if not os.path.exists(script_path):
        return None  # Script doesn't exist
    
    print(f"\n🚀 EJECUTANDO: {os.path.basename(script_path)}")
    print("-" * 50)
    
    # Ensure UTF-8 for subprocesses on Windows
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    
    result = subprocess.run([sys.executable, script_path], capture_output=False, env=env)
    return result.returncode == 0

def main():
    print("====================================================")
    print("🏆 PIPELINE DE CALIDAD GLOBAL - Forecaster Buñuelitos")
    print("====================================================")
    
    # 1. Pruebas Unitarias (MOTOR)
    unit_success = run_script("scripts/run_unit_tests.py")
    if unit_success is False:
        print("\n❌ FALLO CRÍTICO: Pruebas Unitarias no superadas.")
        sys.exit(1)
    elif unit_success is None:
        print("\n⚠️ ADVERTENCIA: No se encontró el script de pruebas unitarias.")
    
    # 2. Pruebas Funcionales (LEYES DE NEGOCIO / MISIÓN)
    functional_success = run_script("scripts/run_functional_tests.py")
    if functional_success is False:
        print("\n❌ FALLO CRÍTICO: Pruebas Funcionales no superadas.")
        sys.exit(1)
    elif functional_success is None:
        print("\nℹ️ NOTA: Saltando pruebas funcionales (No detectadas).")

    # 3. Pruebas de Integración (CONEXIÓN / TUBERÍAS)
    integration_success = run_script("scripts/run_integration_tests.py")
    if integration_success is False:
        print("\n❌ FALLO CRÍTICO: Pruebas de Integración no superadas.")
        sys.exit(1)
    elif integration_success is None:
        print("\nℹ️ NOTA: Saltando pruebas de integración (No detectadas).")
    
    print("\n====================================================")
    print("✅ CERTIFICACIÓN DE CALIDAD GLOBAL COMPLETADA")
    print("====================================================")

if __name__ == "__main__":
    main()
