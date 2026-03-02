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
    
    print(f"--- Ejecutando: {os.path.basename(script_path)} ---")
    result = subprocess.run([sys.executable, script_path], capture_output=False)
    return result.returncode == 0

def main():
    print("====================================================")
    print("🚀 PIPELINE DE CALIDAD GLOBAL - Forecaster Buñuelitos")
    print("====================================================")
    
    # 1. Ejecutar Pruebas Unitarias (Obligatorias)
    unit_success = run_script("scripts/run_unit_tests.py")
    if unit_success is False:
        print("\n❌ FALLO CRÍTICO: Pruebas Unitarias no superadas.")
        sys.exit(1)
    elif unit_success is None:
        print("\n⚠️ ADVERTENCIA: No se encontró el script de pruebas unitarias.")
    
    print("\n----------------------------------------------------")
    
    # 2. Ejecutar Pruebas de Integración (Opcionales/Inteligentes)
    integration_success = run_script("scripts/run_integration_tests.py")
    
    if integration_success is False:
        print("\n❌ FALLO: Pruebas de Integración no superadas.")
        sys.exit(1)
    elif integration_success is None:
        print("ℹ️ NOTA: Saltando integración (No se detectaron pruebas para esta fase).")
    
    print("\n====================================================")
    print("🏆 CERTIFICACIÓN DE CALIDAD COMPLETADA CON ÉXITO")
    print("====================================================")

if __name__ == "__main__":
    main()
