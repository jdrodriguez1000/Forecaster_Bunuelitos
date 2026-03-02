import os
import sys
import json
import yaml
import pandas as pd
from datetime import datetime
import shutil

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.connectors.db_connector import DBConnector
from src.utils.data_health_auditor import DataHealthAuditor

def run_phase_00_audit():
    """
    Main entry point for Phase 00: Initial Exploration & Data Health Audit.
    This script validates the Supabase data against the Data Contract.
    """
    print("--- Starting Phase 00: Initial Exploration & Data Health Audit ---")
    
    # 0. Generate Unique Timestamp for this run
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    
    # Paths (Source)
    contract_latest = "schemas/contract/data_contract_latest.yaml"
    snapshot_latest = "schemas/statistical/initial_statistical_snapshot.json"
    
    # Paths (History - Immutable)
    contract_history = f"schemas/contract/history/data_contract_{timestamp}.yaml"
    snapshot_history = f"schemas/statistical/history/initial_snapshot_{timestamp}.json"
    
    # Ensure history directories exist
    os.makedirs(os.path.dirname(contract_history), exist_ok=True)
    os.makedirs(os.path.dirname(snapshot_history), exist_ok=True)
    
    # Create the updated copies (Double Persistence Protocol)
    with open(contract_latest, "r", encoding="utf-8") as f:
        contract_data = yaml.safe_load(f)
    with open(snapshot_latest, "r", encoding="utf-8") as f:
        snapshot_data = json.load(f)

    # Get Base ID (remove existing timestamp if already present to avoid accumulation)
    base_id = contract_data['metadata']['contract_id']
    parts = base_id.split('_')
    if len(parts) > 4: # v1_YYYY_MM_DD_TIMESTAMP
        base_id = "_".join(parts[:4])
    
    unique_contract_id = f"{base_id}_{timestamp}"
    contract_data['metadata']['contract_id'] = unique_contract_id
    snapshot_data['metadata']['contract_id'] = unique_contract_id

    # Save Updated "Latest" (Sync internal metadata)
    with open(contract_latest, "w", encoding="utf-8") as f:
        yaml.dump(contract_data, f, allow_unicode=True, sort_keys=False)
    with open(snapshot_latest, "w", encoding="utf-8") as f:
        json.dump(snapshot_data, f, indent=4, ensure_ascii=False)

    # Save History (Double Persistence with updated metadata)
    with open(contract_history, "w", encoding="utf-8") as f:
        yaml.dump(contract_data, f, allow_unicode=True, sort_keys=False)
    with open(snapshot_history, "w", encoding="utf-8") as f:
        json.dump(snapshot_data, f, indent=4, ensure_ascii=False)

    print(f"Archived and updated internal IDs: {unique_contract_id}")

    # 1. Initialize Auditor (Gobernanza 2.0)
    # Note: Auditor now expects actual dictionaries/data, not just paths in some versions, 
    # but our current implementation of DataHealthAuditor manages loading if passed paths.
    # Let's pass the data directly for robustness.
    auditor = DataHealthAuditor(contract_data, snapshot_data)
    
    version = contract_data['metadata']['version']

    # Initialize DB Connection
    connector = DBConnector()
    client = connector.get_client()
    
    # Process each table...
    for table_name in contract_data['tables']:
        print(f"Auditing table: {table_name}...")
        try:
            # Pagination logic for Supabase (Pilar 2 Requirement: Full Data)
            all_data = []
            offset = 0
            page_size = 1000
            
            while True:
                response = client.table(table_name).select("*").range(offset, offset + page_size - 1).execute()
                if not response.data:
                    break
                all_data.extend(response.data)
                if len(response.data) < page_size:
                    break
                offset += page_size

            df = pd.DataFrame(all_data) if all_data else pd.DataFrame()
            
            if not df.empty:
                # Basic preprocessing for rules (sort by date)
                if 'fecha' in df.columns:
                    df['fecha'] = pd.to_datetime(df['fecha'])
                    df = df.sort_values('fecha').reset_index(drop=True)
                
                # Perform 4-Pillar Audit
                auditor.audit_dataframe(table_name, df)
                print(f"  [OK] Table {table_name} status: {auditor.report['tables'][table_name]['status']}")
            else:
                print(f"  [!] Warning: No data for {table_name}")
                
        except Exception as e:
            print(f"  [ERROR] Table {table_name} failure: {str(e)}")

    # 2. Save Final Reports (Double Persistence)
    base_reports_path = "outputs/reports/phase_00"
    report_latest = os.path.join(base_reports_path, "phase_00_data_audit_latest.json")
    report_hist = os.path.join(base_reports_path, "history", f"phase_00_audit_{timestamp}.json")
    
    os.makedirs(os.path.dirname(report_hist), exist_ok=True)
    
    # Update Metadata for Report
    auditor.report['metadata'].update({
        "phase": "00",
        "phase_name": "Initial Exploration (Governance 2.0)",
        "execution_mode": "EXPLORE"
    })
    
    auditor.save_report(report_latest)
    auditor.save_report(report_hist)
    print(f"Audit Complete. Global Status: {auditor.report['summary']['status']}")

    # 3. GOVERNANCE: Update Supabase Active Contract
    try:
        print(f"Activating Contract {unique_contract_id} in Supabase...")
        
        # 3.1 Deactivate all previous versions
        client.table("data_contracts").update({"is_active": False}).match({"is_active": True}).execute()
        
        # 3.2 Insert/Activate current version (Fiel al esquema del usuario)
        contract_record = {
            "version": version,
            "contract_id": unique_contract_id,
            "is_active": True,
            "yaml_path": contract_history,
            "snapshot_path": snapshot_history
        }
        res_ins = client.table("data_contracts").insert(contract_record).execute()
        
        if not res_ins.data:
            raise Exception("No se pudo insertar el contrato en Supabase.")
            
        db_contract_id = res_ins.data[0]['id']
        
        # 3.3 Log validation results (Fiel al esquema del usuario)
        validation_record = {
            "contract_id": db_contract_id,
            "status": auditor.report['summary']['status'],
            "health_score": auditor.report['summary']['health_score'],
            "summary_report": auditor.report
        }
        client.table("validation_logs").insert(validation_record).execute()
        
        print(f"  [SUCCESS] Contract {unique_contract_id} is now ACTIVE and Logged.")
    except Exception as e:
        print(f"  [WARNING] Supabase governance sync failed: {str(e)}")
    print("------------------------------------------------------------------")

if __name__ == "__main__":
    run_phase_00_audit()
