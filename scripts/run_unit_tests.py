import os
import sys
import subprocess
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from src.utils.helpers import save_dual_persistence

def main():
    PHASE_ID = "01"
    PHASE_NAME = "Loader & Auditor"
    print(f"🚀 Ejecutando QA - Fase {PHASE_ID}: {PHASE_NAME} (Forecaster Buñuelitos)...")
    
    # Path setup
    base_path = os.path.abspath(os.curdir)
    sys.path.insert(0, base_path)
    
    # Execution command
    report_base = "tests/reports/unit"
    os.makedirs(report_base, exist_ok=True)
    
    cov_file = os.path.join(report_base, "coverage.json")
    xml_file = os.path.join(report_base, "temp_results.xml")

    
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/unit/",
        "-v",
        "--color=no",
        "--cov=src",
        "--cov-report=json",
        f"--cov-report=json:{cov_file}",
        f"--junitxml={xml_file}"
    ]
    
    start_time = datetime.now()
    result = subprocess.run(cmd, capture_output=True, text=True)
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Parse individual test results from XML
    detailed_tests = []
    if os.path.exists(xml_file):
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            for testcase in root.iter('testcase'):
                name = testcase.get('name')
                classname = testcase.get('classname')
                
                # Check for failures or errors
                failure = testcase.find('failure')
                error = testcase.find('error')
                
                status = "PASSED"
                if failure is not None or error is not None:
                    status = "FAILED"
                
                detailed_tests.append({
                    "test_name": name,
                    "class": classname,
                    "status": status
                })
        except Exception as e:
            print(f"⚠️ Error al parsear XML de resultados: {e}")

    # Load coverage stats if available
    coverage_pct = 0.0
    if os.path.exists(cov_file):
        try:
            with open(cov_file, 'r', encoding='utf-8') as f:
                cov_data = json.load(f)
                coverage_pct = cov_data.get('totals', {}).get('percent_covered', 0.0)
        except Exception as e:
            print(f"⚠️ Error al leer cobertura: {e}")

    # Build report data
    report_data = {
        "metadata": {
            "phase_id": PHASE_ID,
            "phase_name": PHASE_NAME,
            "project": "Forecaster Buñuelitos",
            "execution_date": datetime.now().isoformat()
        },
        "summary": {
            "status": "PASSED" if "failed" not in result.stdout.lower() and "error" not in result.stderr.lower() else "FAILED",
            "duration_seconds": round(duration, 3),
            "coverage_percentage": f"{coverage_pct:.2f}%",
            "metrics": {
                "passed": sum(1 for t in detailed_tests if t["status"] == "PASSED"),
                "failed": sum(1 for t in detailed_tests if t["status"] == "FAILED"),
                "total": len(detailed_tests)
            }
        },
        "test_results": detailed_tests,
        "raw_output": {
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    }
    
    # Save using Dual Persistence
    latest_file, history_file = save_dual_persistence(
        data=report_data,
        base_path=report_base,
        filename=f"phase_{PHASE_ID}_unit_tests"
    )
    
    print(f"\n✅ Fase {PHASE_ID} finalizada en {duration:.2f}s")
    print(f"📄 Reporte Detallado Guardado:")
    print(f"   - {latest_file}")
    print(f"   - {history_file}")
    
    if report_data["summary"]["status"] == "FAILED":
        print("\n❌ ALGUNOS TESTS FALLARON. Revisa el reporte para más detalles.")
        sys.exit(1)
    else:
        print(f"\n🏆 TODO CORRECTO PARA LA FASE {PHASE_ID}.")

if __name__ == "__main__":
    main()

