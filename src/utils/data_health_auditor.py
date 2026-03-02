import os
import json
import yaml
import pandas as pd
import numpy as np
from datetime import datetime
from src.utils.business_rules_engine import BusinessRulesEngine

class DataHealthAuditor:
    """
    Class responsible for auditing data health against a Data Contract (YAML)
    and a Statistical Snapshot (JSON).
    """

    def __init__(self, contract_path, snapshot_path):
        self.contract_path = contract_path
        self.snapshot_path = snapshot_path
        self.contract = self._load_yaml(contract_path)
        self.snapshot = self._load_json(snapshot_path)
        self.rules_engine = BusinessRulesEngine()
        self.report = {
            "metadata": {
                "phase": "00", # Default, should be updated by caller
                "phase_name": "Unknown Phase",
                "execution_mode": "EXPLORE",
                "audit_timestamp": datetime.now().isoformat(),
                "contract_id": self.contract['metadata']['contract_id'],
                "contract_version": self.contract['metadata']['version']
            },
            "summary": {
                "total_violations": 0,
                "failure_count": 0,
                "warning_count": 0,
                "status": "SUCCESS",
                "health_score": 100.0
            },
            "tables": {}
        }

    def set_metadata(self, phase, phase_name, execution_mode):
        """Updates the metadata for the report."""
        self.report['metadata']['phase'] = phase
        self.report['metadata']['phase_name'] = phase_name
        self.report['metadata']['execution_mode'] = execution_mode

    def set_contract_id(self, contract_id):
        """Updates the contract_id in the report metadata."""
        self.report['metadata']['contract_id'] = contract_id

    def _load_yaml(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _load_json(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def audit_dataframe(self, table_name, df, horizon_days=185):
        """
        Runs the audit for a specific table's DataFrame.
        """
        if table_name not in self.contract['tables']:
            return {"status": "error", "message": f"Table {table_name} not found in contract"}

        table_contract = self.contract['tables'][table_name]
        table_snapshot = self.snapshot['tables'].get(table_name, {})
        
        table_report = {
            "status": "SUCCESS", # Default, updated during audit
            "ingestion_type": "UNKNOWN", # Updated by loader
            "compliance_summary": "", # human readable recap
            "critical_message": "", # ONLY for FAILURE
            "compliance": {
                "matched_columns": [],
                "missing_columns": [],
                "extra_columns": []
            },
            "successes": [],
            "violations": [],
            "stats": {
                "row_count": len(df),
                "null_pct": float(df.isnull().mean().mean()) if not df.empty else 0.0,
                "integrity": {
                    "duplicate_rows": 0,
                    "duplicate_dates": 0,
                    "temporal_gaps": 0,
                    "sentinel_count": 0
                }
            }
        }

        # 1. Integrity Validation (Duplicates & Gaps)
        self._audit_integrity_checks(table_name, df, table_report)

        # 0. Schema Hierarchy Check
        contract_cols = set(table_contract.get('columns', {}).keys())
        data_cols = set(df.columns)
        
        table_report['compliance']['matched_columns'] = list(data_cols & contract_cols)
        table_report['compliance']['missing_columns'] = list(contract_cols - data_cols)
        table_report['compliance']['extra_columns'] = list(data_cols - contract_cols)
        
        # Log missing columns as failures
        if table_report['compliance']['missing_columns']:
            table_report['status'] = "FAILURE"
            self._add_violation(table_report, "FAILURE", f"Missing required columns: {table_report['compliance']['missing_columns']}")

        # Log extra columns as warnings
        if table_report['compliance']['extra_columns']:
            if table_report['status'] != "FAILURE":
                table_report['status'] = "WARNING"
            self._add_violation(table_report, "WARNING", f"Uncontracted columns detected (Schema Drift): {table_report['compliance']['extra_columns']}")
        
        if not table_report['compliance']['missing_columns'] and not table_report['compliance']['extra_columns']:
            self._add_success(table_report, "Schema matches contract exactly.")

        # 1. Structural Validation (Types & Existence)
        for col_name, col_rules in table_contract.get('columns', {}).items():
            if col_name not in df.columns:
                self._add_violation(table_report, "FAILURE", f"Column '{col_name}' missing")
                continue

            # Null Check
            null_pct = float(df[col_name].isnull().mean())
            max_null = self.contract['global_standards']['integrity_defaults']['null_management']['default_max_null_pct']
            if col_rules.get('required') and null_pct > 0:
                 self._add_violation(table_report, "FAILURE", f"Column '{col_name}' is required but has nulls")
            elif null_pct > max_null:
                 self._add_violation(table_report, "WARNING", f"Column '{col_name}' exceeds null tolerance ({null_pct:.2%})")
            else:
                 self._add_success(table_report, f"Column '{col_name}' null percentage within tolerance ({null_pct:.2%})")

            # Category Check (Map to Others)
            if 'categories' in col_rules:
                allowed = set(col_rules['categories'])
                unique_vals = set(df[col_name].dropna().unique())
                unknowns = unique_vals - allowed
                if unknowns:
                    action = col_rules.get('on_unknown', 'map_to_others')
                    severity = self.contract['global_standards']['integrity_defaults']['unknown_categories']['severity']
                    self._add_violation(table_report, severity, f"Unknown categories in '{col_name}': {list(unknowns)}. Action: {action}")
                else:
                    self._add_success(table_report, f"Column '{col_name}' categorical values within allowed list")

            # Sentinel Check (Per Column)
            self._check_sentinels(col_name, df, table_report)

        # 2. Monitoring Strategy (Drift Detection: Internal History vs Horizon)
        if 'monitoring_strategy' in self.contract:
            drift_thresh = self.contract['monitoring_strategy']['trend_analysis']['drift_threshold_pct'] / 100
            # horizon_days is now a function parameter

            for col_name in df.select_dtypes(include=['number']).columns:
                if col_name in table_snapshot.get('columns', {}):
                    hist_mean = table_snapshot['columns'][col_name].get('mean')
                    if hist_mean and hist_mean != 0:
                        # 2.1 Global Drift (All available history)
                        curr_mean = float(df[col_name].mean())
                        drift = abs(curr_mean - hist_mean) / hist_mean
                        if drift > drift_thresh:
                            self._add_violation(table_report, "WARNING", f"Global Trend Drift detected in '{col_name}': {drift:.2%} deviation from snapshot (Full History)")
                        else:
                            self._add_success(table_report, f"No Global Drift detected in '{col_name}' (Deviation: {drift:.2%})")

                        # 2.2 Horizon Drift (Last 185 days - The 'Launchpad' for forecasting)
                        if 'fecha' in df.columns:
                            # Robust conversion to ensure arithmetic works
                            temp_fecha = pd.to_datetime(df['fecha'])
                            latest_date = temp_fecha.max()
                            horizon_start = latest_date - pd.Timedelta(days=horizon_days)
                            horizon_df = df[temp_fecha >= horizon_start]
                            
                            if not horizon_df.empty:
                                horizon_mean = float(horizon_df[col_name].mean())
                                h_drift = abs(horizon_mean - hist_mean) / hist_mean
                                if h_drift > drift_thresh:
                                    self._add_violation(table_report, "WARNING", f"Horizon Drift detected in '{col_name}': {h_drift:.2%} deviation in last {horizon_days} days")
                                else:
                                    self._add_success(table_report, f"No Horizon Drift detected in '{col_name}' in last {horizon_days} days (Deviation: {h_drift:.2%})")

        # 3. Business Rules Validation (New)
        if 'rules' in table_contract:
            for rule_name, rule_body in table_contract.get('rules', {}).items():
                rule_str = rule_body.get('rule')
                condition = rule_body.get('condition')
                severity = rule_body.get('severity', 'WARNING')
                
                # If there's a condition, prepend it (IF condition THEN rule)
                full_rule = f"if ({condition}) then ({rule_str})" if condition else rule_str
                
                # Run the rules engine!
                results = self.rules_engine.evaluate_rule(df, full_rule)
                failures = len(results) - results.sum()
                
                if failures > 0:
                    fail_pct = (failures / len(df)) * 100
                    msg = f"Business Rule '{rule_name}' violated in {failures} rows ({fail_pct:.1f}%). Rule: {full_rule}"
                    self._add_violation(table_report, severity, msg)
                else:
                    self._add_success(table_report, f"Business Rule '{rule_name}' passed (0 violations)")

            # Cleanup temp columns (if any created for t-1/lags)
            self.rules_engine.cleanup_temps(df)

        # Final Status & Critical Message Logic
        if table_report['status'] == "FAILURE":
            table_report['critical_message'] = "CRÍTICO: NO CONTINUAR"
        
        # Human readable compliance summary
        matched = len(table_report['compliance']['matched_columns'])
        missing = len(table_report['compliance']['missing_columns'])
        extra = len(table_report['compliance']['extra_columns'])
        table_report['compliance_summary'] = f"Matched: {matched} | Missing: {missing} | Extras: {extra}"

        self.report['tables'][table_name] = table_report
        return table_report

    def _audit_integrity_checks(self, table_name, df, table_report):
        """Internal method to check for duplicates and temporal continuity."""
        if df.empty:
            return

        # A. Global Duplicates (Exact row matches)
        dups_count = int(df.duplicated().sum())
        table_report['stats']['integrity']['duplicate_rows'] = dups_count
        if dups_count > 0:
            self._add_violation(table_report, "WARNING", f"Detected {dups_count} exact duplicate rows.")

        # B. Temporal Logic (Dates and Gaps)
        if 'fecha' in df.columns:
            # Duplicate Dates
            date_dups = int(df['fecha'].duplicated().sum())
            table_report['stats']['integrity']['duplicate_dates'] = date_dups
            if date_dups > 0:
                self._add_violation(table_report, "WARNING", f"Detected {date_dups} duplicate dates (multiple records for same day).")

            # Temporal Gaps (Holes in the series)
            try:
                temp_dates = pd.to_datetime(df['fecha']).dt.date
                date_range = pd.date_range(start=temp_dates.min(), end=temp_dates.max(), freq='D').date
                missing_dates = set(date_range) - set(temp_dates)
                gaps_count = len(missing_dates)
                table_report['stats']['integrity']['temporal_gaps'] = gaps_count
                
                if gaps_count > 0:
                    self._add_violation(table_report, "WARNING", f"Data continuity breach: {gaps_count} missing days found in the time series.")
                else:
                    self._add_success(table_report, "No temporal gaps found. Time series is continuous.")
            except Exception as e:
                # Silently skip if date conversion fails, common in raw dirty data
                pass

    def _check_sentinels(self, col_name, df, table_report):
        """Checks for sentinel values (dummy markers) in a column."""
        sentinels = self.contract.get('global_standards', {}).get('sentinel_values', {})
        if not sentinels or df[col_name].empty:
            return

        # Map pandas dtypes to contract categories
        dtype = str(df[col_name].dtype)
        category = "object"
        if "int" in dtype or "float" in dtype:
            category = "numeric"
        elif "datetime" in dtype:
            category = "datetime"
        elif "bool" in dtype:
            category = "boolean"
        
        target_sentinels = sentinels.get(category, [])
        if not target_sentinels:
            return

        # Standardize for comparison (especially for dates)
        comparison_sentinels = target_sentinels
        if category == "datetime":
            comparison_sentinels = pd.to_datetime(target_sentinels)

        # Check for hits
        hits_mask = df[col_name].isin(comparison_sentinels)
        hits = hits_mask.sum()
        
        if hits > 0:
            found_sentinels = df[hits_mask][col_name].unique().tolist()
            pct = (hits / len(df)) * 100
            table_report['stats']['integrity']['sentinel_count'] += int(hits)
            
            # Convert found values to strings for clean JSON reporting
            found_str = [str(s) for s in found_sentinels]
            
            self._add_violation(
                table_report, 
                "WARNING", 
                f"Sentinel value(s) detected in '{col_name}': {hits} instances ({pct:.1f}%). Found: {found_str}"
            )

    def audit_freshness(self, table_name, df, ref_date):
        """
        Validates if the latest data in the DataFrame is current relative to a reference date.
        Today (Feb 28/Mar 1): PASS
        1 day delay: WARNING
        2+ days delay: FAILURE
        """
        if 'fecha' not in df.columns or df.empty:
            return

        latest_date = pd.to_datetime(df['fecha']).max().date()
        ref_date = pd.to_datetime(ref_date).date()
        
        # Calculate days difference (Target: Feb 28th should be SUCCESS for Mar 1st ref)
        delta = (ref_date - latest_date).days
        
        table_report = self.report['tables'].get(table_name, {"status": "SUCCESS", "violations": [], "stats": {}})
        
        if delta <= 1: # Represents Feb 28th if ref is Mar 1st
            self._add_success(table_report, f"Freshness Check: Data is up to date (Latest: {latest_date})")
        elif delta == 2: # Represents Feb 27th
            self._add_violation(table_report, "WARNING", f"Freshness Check: Data delay of 2 days (Latest: {latest_date})")
        else: # Feb 26 or older
            self._add_violation(table_report, "FAILURE", f"Freshness Check: CRITICAL delay of {delta} days (Latest: {latest_date})")
            
        table_report['stats']['freshness_days'] = int(delta)
        table_report['stats']['latest_date'] = str(latest_date)
        self.report['tables'][table_name] = table_report

    def _add_violation(self, table_report, severity, message):
        violation = {"severity": severity, "message": message}
        table_report['violations'].append(violation)
        self.report['summary']['total_violations'] += 1
        
        # 1. Update Table Level Status (Hierarchy: FAILURE > WARNING > SUCCESS)
        if severity == "FAILURE":
            table_report['status'] = "FAILURE"
        elif severity == "WARNING":
            if table_report.get('status') != "FAILURE":
                table_report['status'] = "WARNING"

        # 2. Update Global Summary Status
        if severity == "FAILURE":
            self.report['summary']['failure_count'] += 1
            self.report['summary']['status'] = "FAILURE"
        else:
            self.report['summary']['warning_count'] += 1
            if self.report['summary']['status'] != "FAILURE":
                self.report['summary']['status'] = "WARNING"

    def _add_success(self, table_report, message):
        success = {"status": "SUCCESS", "message": message}
        if "successes" not in table_report:
            table_report["successes"] = []
        table_report['successes'].append(success)

    def calculate_score(self):
        """Calculates and returns the health score based on failures and warnings."""
        failures = self.report['summary']['failure_count']
        warnings = self.report['summary']['warning_count']
        score = max(0, 100 - (failures * 10) - (warnings * 1))
        self.report['summary']['health_score'] = float(score)
        return float(score)

    def save_report(self, output_path):
        score = self.calculate_score()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.report, f, indent=4, ensure_ascii=False)
        print(f"Audit report saved at {output_path} (Health Score: {score})")
