import os
import yaml
import json
import pandas as pd
from datetime import datetime
import logging
from src.connectors.db_connector import DBConnector
from src.utils.data_health_auditor import DataHealthAuditor

logger = logging.getLogger(__name__)

class DataLoader:
    """
    Data Loader Module
    Extracts data from Supabase incrementally and validates against Data Contract.
    """
    def __init__(self, config):
        self.config = config
        self.db = DBConnector()
        self.client = self.db.get_client()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Handshake: Get active contract and laws from Supabase View
        self.contract_metadata = self._handshake()
        self.contract_path = self.contract_metadata['ruta_contrato_yaml']
        self.snapshot_path = self.contract_metadata['ruta_snapshot_json']
        self.contract_id = self.contract_metadata['contract_id'] # TU código texto (v1_...)
        self.internal_contract_id = self.contract_metadata['contract_db_id'] # ID numérico (BIGINT)
        
        # Initialize Auditor with the rules from the nube
        self.auditor = DataHealthAuditor(self.contract_path, self.snapshot_path)

    def _handshake(self):
        """Query the v_latest_data_health view to get the active law."""
        logger.info("Performing Handshake with Supabase Control Plane...")
        res = self.client.table("v_latest_data_health").select("*").eq("es_contrato_activo", True).limit(1).execute()
        
        if not res.data:
            logger.error("Critical Error: No active Data Contract found in v_latest_data_health view.")
            raise RuntimeError("Handshake failed: No active Data Contract.")
        
        logger.info(f"Handshake successful. Active Contract: {res.data[0]['contract_id']}")
        return res.data[0]

    def _get_incremental_info(self, table_name):
        """Check the data_inventory_status for the last data date. Upsert if not exists."""
        res = self.client.table("data_inventory_status").select("*").eq("table_name", table_name).execute()
        
        if not res.data:
            # Option A: Dinamically create the record
            logger.info(f"Table '{table_name}' not found in inventory status. Initializing...")
            new_record = {
                "table_name": table_name,
                "last_data_date": "1900-01-01",
                "status": "PENDING",
                "contract_id": self.internal_contract_id
            }
            res_ins = self.client.table("data_inventory_status").insert(new_record).execute()
            return res_ins.data[0]
        
        return res.data[0]

    def _download_delta(self, table_name, last_date):
        """Download records where fecha > last_date using pagination."""
        logger.info(f"Downloading delta for '{table_name}' since {last_date}...")
        all_data = []
        offset = 0
        page_size = 1000
        
        while True:
            # Note: We filter by 'fecha' as a standard column across all project tables
            query = self.client.table(table_name).select("*").gt("fecha", last_date).order("fecha").range(offset, offset + page_size - 1)
            response = query.execute()
            
            if not response.data:
                break
            
            all_data.extend(response.data)
            if len(response.data) < page_size:
                break
            offset += page_size
            
        return pd.DataFrame(all_data)

    def process_all_tables(self):
        """Main loop for ingestion, validation and persistence."""
        summary_results = {}
        tables_to_process = self.config['extractions']['tables']
        raw_path = self.config['general']['data_raw_path']
        os.makedirs(raw_path, exist_ok=True)

        # Forensic Report collection
        forensic_reports = {}

        for table in tables_to_process:
            logger.info(f"--- Processing Table: {table} ---")
            
            # 1. Get Inventory Context
            inventory_info = self._get_incremental_info(table)
            last_date = inventory_info['last_data_date']
            
            # 2. Download to Memory (Buffer)
            df_new = self._download_delta(table, last_date)
            
            if df_new.empty:
                logger.info(f"No new data found for table '{table}'. Checking local mirror for report consistency.")
                local_file = os.path.join(raw_path, f"{table}.parquet")
                
                if os.path.exists(local_file):
                    df_audit = pd.read_parquet(local_file)
                    status_prefix = "NO_NEW_DATA" # Custom status for skipped ingest
                    ingestion_type = "NO_NEW_DATA"
                else:
                    # No data anywhere
                    forensic_reports[table] = {
                        "status": "NO_DATA",
                        "ingestion_type": "NO_DATA",
                        "new_rows_count": 0,
                        "compliance_summary": "No data in Supabase nor Local disk",
                        "compliance": {"matched_columns": [], "missing_columns": [], "extra_columns": []},
                        "successes": [],
                        "violations": [{"severity": "FAILURE", "message": "CRÍTICO: NO CONTINUAR - NO HAY DATOS"}],
                        "stats": {"row_count": 0, "null_pct": 0},
                        "health_score": 0
                    }
                    summary_results[table] = "NO_DATA"
                    continue
            else:
                df_audit = df_new
                ingestion_type = "FULL" if not os.path.exists(os.path.join(raw_path, f"{table}.parquet")) else "INCREMENTAL"

            # 3. Validation and Audit (The Aduana)
            # Reset auditor internal counters for single table run
            self.auditor.report['summary'] = {"total_violations": 0, "failure_count": 0, "warning_count": 0, "status": "SUCCESS"}
            
            audit_report = self.auditor.audit_dataframe(table, df_audit)
            
            # Map Ingestion and New Row count
            audit_report['ingestion_type'] = ingestion_type
            audit_report['new_rows_count'] = len(df_new) if not df_new.empty else 0
            
            # If NO_NEW_DATA, we append the info but keep the health score of what we have
            if df_new.empty:
                # Add notice that it was a local audit
                audit_report['message'] = "Audit performed on local data (No Delta download)."
            
            # Calculate health score 
            hs = self.auditor.calculate_score()
            audit_report['health_score'] = hs
            
            # Final Status (Table result)
            status = audit_report['status']
            
            # Update collection with full forensic details
            forensic_reports[table] = audit_report
            logger.info(f"Audit Result for '{table}': HP {hs} | State: {status} | Ingest: {ingestion_type}")

            # 4. Decision: Persist or Abort
            if status == "FAILURE":
                logger.error(f"FAILURE for table '{table}'. NO CONTINUAR.")
                self._log_and_notify(table, status, audit_report, inventory_info)
                summary_results[table] = "FAILURE"
                continue # Skip persistence but keep processing other tables

            if not df_new.empty:
                # SUCCESS or WARNING (Incremental/Full) -> Persist
                local_file = os.path.join(raw_path, f"{table}.parquet")
                
                # FUSION: Merge with local history if exists
                if os.path.exists(local_file):
                    df_local = pd.read_parquet(local_file)
                    df_combined = pd.concat([df_local, df_new], ignore_index=True)
                    df_combined = df_combined.drop_duplicates(subset=['fecha'], keep='last').sort_values('fecha')
                else:
                    df_combined = df_new.sort_values('fecha')

                # Save to disk (The Truth Zone)
                df_combined.to_parquet(local_file, index=False)
                logger.info(f"Persisted '{table}'. Total Rows: {len(df_combined)}")

                # Update Control Plane
                self._update_inventory_status(table, df_combined, df_new, status, hs, inventory_info)
                self._log_and_notify(table, status, audit_report, inventory_info)
                summary_results[table] = status
            else:
                # No new data, just report the last status found in the local audit
                summary_results[table] = status

        self._save_phase_report(forensic_reports)
        return summary_results

    def _update_inventory_status(self, table, df_all, df_new, status, health_score, info):
        """Update the data_inventory_status table in Supabase."""
        max_date = str(df_new['fecha'].max())
        update_data = {
            "last_execution": datetime.now().isoformat(),
            "last_data_date": max_date,
            "row_count": len(df_all),
            "health_score": health_score,
            "status": status,
            "contract_id": self.internal_contract_id,
            "updated_at": datetime.now().isoformat()
        }
        self.client.table("data_inventory_status").update(update_data).eq("table_name", table).execute()

    def _log_and_notify(self, table, status, report, info):
        """Insert the audit result into validation_logs."""
        log_entry = {
            "contract_id": self.internal_contract_id,
            "status": status,
            "health_score": report['health_score'],
            "summary_report": report
        }
        self.client.table("validation_logs").insert(log_entry).execute()

    def _save_phase_report(self, summary):
        """Save a local JSON report of the entire phase execution following MLOps standards."""
        base_reports_path = os.path.join(self.config['general']['outputs_path'], "reports", "phase_01")
        history_path = os.path.join(base_reports_path, "history")
        
        os.makedirs(history_path, exist_ok=True)
        
        phase_report = {
            "metadata": {
                "phase": "01",
                "phase_name": "Data Loading & Validation",
                "execution_mode": self.config['general']['mode'],
                "timestamp": self.timestamp,
                "contract_code": self.contract_id,
                "contract_db_id": self.internal_contract_id
            },
            "execution_summary": {
                "total_tables": len(summary),
                "success_count": sum(1 for v in summary.values() if v['status'] == "SUCCESS"),
                "warning_count": sum(1 for v in summary.values() if v['status'] == "WARNING"),
                "failure_count": sum(1 for v in summary.values() if v['status'] == "FAILURE"),
                "overall_status": "FAILURE" if any(v['status'] == "FAILURE" for v in summary.values()) else ("WARNING" if any(v['status'] == "WARNING" for v in summary.values()) else "SUCCESS")
            },
            "tables": summary
        }
        
        # 1. Save History (Immutable)
        hist_file = os.path.join(history_path, f"phase_01_loader_{self.timestamp}.json")
        with open(hist_file, "w", encoding="utf-8") as f:
            json.dump(phase_report, f, indent=4, ensure_ascii=False)
        
        # 2. Save Latest (Pointer)
        latest_file = os.path.join(base_reports_path, "phase_01_loader_latest.json")
        with open(latest_file, "w", encoding="utf-8") as f:
            json.dump(phase_report, f, indent=4, ensure_ascii=False)
            
        logger.info(f"Phase 01 audit reports saved at {base_reports_path} (Latest & History)")
