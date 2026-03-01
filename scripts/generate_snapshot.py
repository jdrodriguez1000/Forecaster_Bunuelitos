import os
import sys
import json
import yaml
import pandas as pd
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.connectors.db_connector import DBConnector

def generate_initial_snapshot():
    # Load the Data Contract (v1.3)
    contract_path = "schemas/contract/data_contract_latest.yaml"
    with open(contract_path, "r", encoding="utf-8") as f:
        contract = yaml.safe_load(f)
    
    # Generate Timestamp (aligned with explorer.py)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Get Base ID (remove existing timestamp if present)
    base_id = contract['metadata']['contract_id']
    parts = base_id.split('_')
    if len(parts) > 4: # v1_YYYY_MM_DD_TIMESTAMP
        base_id = "_".join(parts[:4])
    
    full_contract_id = f"{base_id}_{timestamp}"
    version = contract['metadata']['version']
    
    # Initialize DB Connection
    connector = DBConnector()
    client = connector.get_client()
    
    snapshot = {
        "metadata": {
            "contract_id": full_contract_id,
            "contract_version": version,
            "generated_at": datetime.now().isoformat(),
            "lookback_period_days": contract.get('monitoring_strategy', {}).get('trend_analysis', {}).get('lookback_period_days', 185)
        },
        "tables": {}
    }
    
    # Process each table in the contract
    for table_name, table_info in contract['tables'].items():
        print(f"Processing table: {table_name}...")
        try:
            # Query data from Supabase
            # NOTE: Assuming the table names in Supabase match the keys in 'tables' section
            response = client.table(table_name).select("*").execute()
            data = response.data
            
            if not data:
                print(f"Warning: No data found for table {table_name}")
                snapshot["tables"][table_name] = {"status": "empty"}
                continue
            
            df = pd.DataFrame(data)
            
            # Basic stats for numerical columns
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            table_stats = {
                "row_count": len(df),
                "columns": {}
            }
            
            for col in df.columns:
                col_stats = {
                    "type": str(df[col].dtype),
                    "null_count": int(df[col].isnull().sum()),
                    "null_pct": float(df[col].isnull().mean())
                }
                
                if col in numeric_cols:
                    col_stats.update({
                        "min": float(df[col].min()),
                        "max": float(df[col].max()),
                        "mean": float(df[col].mean()),
                        "std": float(df[col].std()),
                        "q25": float(df[col].quantile(0.25)),
                        "q50": float(df[col].quantile(0.50)),
                        "q75": float(df[col].quantile(0.75))
                    })
                elif df[col].dtype == 'object' or isinstance(df[col].iloc[0], str):
                    # Categorical stats
                    counts = df[col].value_counts()
                    col_stats["categories"] = counts.to_dict()
                    col_stats["unique_count"] = len(counts)
                
                table_stats["columns"][col] = col_stats
            
            snapshot["tables"][table_name] = table_stats
            
        except Exception as e:
            print(f"Error processing table {table_name}: {str(e)}")
            snapshot["tables"][table_name] = {"status": "error", "error": str(e)}

    # Save the 'Latest' Snapshot
    output_path = "schemas/statistical/initial_statistical_snapshot.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=4, ensure_ascii=False)
    
    # Save History version
    history_path = f"schemas/statistical/history/initial_snapshot_{timestamp}.json"
    os.makedirs(os.path.dirname(history_path), exist_ok=True)
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=4, ensure_ascii=False)
    
    print(f"Snapshot generated successfully at {output_path} with ID {full_contract_id}")

if __name__ == "__main__":
    generate_initial_snapshot()
