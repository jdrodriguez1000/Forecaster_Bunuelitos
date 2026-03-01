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

    # 1. Initialize Auditor & Load Data
    auditor = DataHealthAuditor(contract_history, snapshot_history)
    auditor.set_contract_id(unique_contract_id) # Update in the JSON metadata
    
    version = auditor.contract['metadata']['version']

    # Initialize DB Connection
    connector = DBConnector()
    client = connector.get_client()
    
    # Process each table...
    for table_name in auditor.contract['tables']:
        print(f"Auditing table: {table_name}...")
        try:
            # Pagination logic to bypass 1000 record limit
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
                # Ensure data is sorted by date for time-lagged rules (t_minus_1)
                if 'fecha' in df.columns:
                    df['fecha'] = pd.to_datetime(df['fecha'])
                    df = df.sort_values('fecha').reset_index(drop=True)
                    # Support for calendar-based rules (e.g., ads shutdown on day 25)
                    df['day'] = df['fecha'].dt.day
                
                auditor.audit_dataframe(table_name, df)
                # Ensure it's up to date! (Requirement 1)
                auditor.audit_freshness(table_name, df, now.date()) 
            else:
                print(f"Warning: No data for {table_name}")
        except Exception as e:
            print(f"Error auditing table {table_name}: {str(e)}")

    # 2. Save Final Reports (Double Persistence for the audit report)
    latest_report = "outputs/reports/phase_00_data_audit_latest.json"
    history_report = f"outputs/reports/phase_00/history/data_audit_{timestamp}.json"
    
    auditor.save_report(latest_report) # Save latest
    auditor.save_report(history_report) # Save history
    
    # 3. Sync with DB (using Immutable Paths)
    # Deactivate previous active contract
    client.table("data_contracts").update({"is_active": False}).match({"is_active": True}).execute()
    
    # Insert new record pointing to History files
    print(f"Registering new Active Contract: {unique_contract_id}")
    res_ins = client.table("data_contracts").insert({
        "version": version,
        "contract_id": unique_contract_id,
        "yaml_path": contract_history,
        "snapshot_path": snapshot_history,
        "is_active": True
    }).execute()
    
    db_contract_id = res_ins.data[0]['id']
    
    # Upload Log
    print("Uploading audit log...")
    client.table("validation_logs").insert({
        "contract_id": db_contract_id,
        "status": auditor.report['summary']['status'],
        "health_score": auditor.report['summary']['health_score'],
        "summary_report": auditor.report
    }).execute()
    
    print(f"Workflow finished. Health Score: {auditor.report['summary']['health_score']}")
    print("------------------------------------------------------------------")

if __name__ == "__main__":
    run_phase_00_audit()
