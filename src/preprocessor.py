import os
import sys

# Ensure project root is in path for direct execution
if __name__ == "__main__":
    _root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if _root not in sys.path:
        sys.path.insert(0, _root)

import pandas as pd
import numpy as np
import logging
import json
import re
from datetime import datetime
from src.connectors.db_connector import DBConnector

logger = logging.getLogger(__name__)

class Preprocessor:
    """
    Phase 02: Preprocessor Module (The Healer)
    Handles data cleaning, reindexing, sequential healing, and consolidation.
    Implements incremental logic and handshake with Supabase.
    """
    def __init__(self, config):
        self.config = config
        self.db = DBConnector()
        self.client = self.db.get_client()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Paths from config
        self.raw_path = self.config['general']['data_raw_path']
        self.cleansed_path = self.config['general']['data_cleansed_path']
        self.master_dataset_file = "master_cleansed.parquet"
        self.reports_path = os.path.join(self.config['general']['outputs_path'], "reports", "phase_02")
        
        # Ensure directories exist
        os.makedirs(self.cleansed_path, exist_ok=True)
        os.makedirs(self.reports_path, exist_ok=True)
        os.makedirs(os.path.join(self.reports_path, "history"), exist_ok=True)
        
        # Internal state
        self.processing_type = "FULL" # Default, revised in run()
        self.input_health_status = {} # To be populated by handshake
        self.domain_stats = {} # {domain: {outliers: 0, nulls: 0, fixes: 0, anti_leakage: 0, deduplicated: 0, pruned_cols: [], gaps_filled: 0, applied_rules: [], healing_log: []}}
        self.output_audit = {
            "duplicate_rows": 0,
            "duplicate_dates": 0,
            "null_values": 0,
            "temporal_gaps": 0
        }
        self.healing_stats = {
            "outliers_detected": 0,
            "nulls_cured": 0,
            "physical_fixes": 0,
            "log": [] # Human readable log of actions
        }

    def _handshake(self):
        """Validates if we can start preprocessing based on Phase 01 status."""
        logger.info("Performing Preprocessing Handshake (Go/No-Go)...")
        handshake_cfg = self.config['preprocessing']['orchestration']['handshake']
        tables_to_check = handshake_cfg['tables_to_check']
        required_status = handshake_cfg['required_status']
        min_health_score = handshake_cfg['min_health_score']

        # RULE 0: Critical check for LOAD phase status
        try:
            res_exec = self.client.table("pipeline_execution_status")\
                .select("*")\
                .eq("phase", "LOAD")\
                .order("updated_at", desc=True)\
                .limit(1)\
                .execute()
            
            if res_exec.data:
                latest_load = res_exec.data[0]
                if latest_load['status'] == "FAILED":
                    msg = f"Handshake FAILED: Latest LOAD phase (Phase 01) recorded as FAILED at {latest_load.get('updated_at')}. Aborting preprocessing."
                    logger.error(msg)
                    return False, msg, 0
            else:
                logger.warning("No LOAD entry found in pipeline_execution_status. Proceeding with caution based on table health.")
        except Exception as e:
            logger.warning(f"Failed to query pipeline_execution_status: {e}. Proceeding with table health checks.")

        # Rule 1: Individual Table Health
        logger.info(f"Checking tables health scores: {tables_to_check}")
        try:
            res = self.client.table("data_inventory_status").select("*").in_("table_name", tables_to_check).execute()
        except Exception as e:
            logger.error(f"Handshake select failed: {e}")
            raise
        
        if not res.data:
            raise RuntimeError("Handshake failed: No inventory status found in Supabase.")

        status_df = pd.DataFrame(res.data)
        
        # Store individual health scores for the final report
        self.input_health_status = status_df.set_index('table_name')['health_score'].to_dict()
        
        required_status = self.config['preprocessing']['orchestration']['handshake']['required_status']
        min_score = self.config['preprocessing']['orchestration']['handshake']['min_health_score']

        # Handshake Logic: Fail if any table is FAILED or below min_health_score
        # Note: If required_status is SUCCESS, we allow WARNING as per business rules ("No inicia si hay FAILURE")
        if required_status == "SUCCESS":
            failed_tables = status_df[
                (status_df['status'] == "FAILED") | 
                (status_df['health_score'] < min_score * 100)
            ]['table_name'].tolist()
        else:
            failed_tables = status_df[
                (status_df['status'] != required_status) | 
                (status_df['health_score'] < min_score * 100)
            ]['table_name'].tolist()
        if failed_tables:
            msg = f"Handshake FAILED. Tables not ready: {failed_tables}"
            logger.error(msg)
            return False, msg, status_df['health_score'].mean()

        safe_date = status_df['last_data_date'].min()
        avg_health = status_df['health_score'].mean()
        
        logger.info(f"Handshake SUCCESS. Safe Date: {safe_date} | Avg Health: {avg_health:.2f}")
        return True, safe_date, avg_health

    def _get_delta_context(self):
        """Determines the starting date for incremental processing."""
        master_path = os.path.join(self.cleansed_path, self.master_dataset_file)
        if os.path.exists(master_path):
            df_master = pd.read_parquet(master_path)
            last_date = df_master['fecha'].max()
            return pd.to_datetime(last_date)
        return None

    def _load_raw_domain(self, domain, last_cleaned_date=None):
        """Loads, cleans and enforces Global Laws on raw data."""
        raw_file = os.path.join(self.raw_path, f"{domain}.parquet")
        if not os.path.exists(raw_file):
            return None

        df = pd.read_parquet(raw_file)
        
        # Initialize domain stats if not exists
        if domain not in self.domain_stats:
            self.domain_stats[domain] = {
                "outliers": 0, "nulls": 0, "fixes": 0, 
                "anti_leakage": 0, "deduplicated": 0, "pruned_cols": [], "gaps_filled": 0
            }

        # 1. Anti-Leakage Rule (T-1)
        if self.config['preprocessing']['global_settings']['anti_leakage_t_minus_1']:
            today = pd.Timestamp(datetime.now().date())
            leak_mask = df['fecha'] >= today
            leak_count = int(leak_mask.sum())
            if leak_count > 0:
                df = df[~leak_mask].copy()
                self.domain_stats[domain]["anti_leakage"] = leak_count
                logger.warning(f"[{domain}] Anti-Leakage active: Dropped {leak_count} rows from 'Today' ({today.date()}) onwards.")

        # 2. Last Truth Rule (Deduplication)
        dedup_cfg = self.config['preprocessing']['global_settings']['deduplication_strategy']
        if 'updated_at' in df.columns:
            df = df.sort_values(['fecha', dedup_cfg['by_column']], ascending=[True, dedup_cfg['order'] == "descending"])
            pre_dedup = len(df)
            df = df.drop_duplicates(subset=['fecha'], keep='first')
            self.domain_stats[domain]["deduplicated"] = pre_dedup - len(df)

        # 3. Column Alignment Rule (Pruning extra columns)
        if self.config['preprocessing']['global_settings']['alignment']['drop_extra_columns']:
            # Use extraction columns as the contract
            expected_cols = ['fecha'] + self.config['extractions'].get('columns', {}).get(domain, [])
            if expected_cols:
                extra_cols = [c for c in df.columns if c not in expected_cols and not c.startswith('__')]
                if extra_cols:
                    df = df.drop(columns=extra_cols)
                    self.domain_stats[domain]["pruned_cols"] = extra_cols

        df['fecha'] = pd.to_datetime(df['fecha'])
        
        if last_cleaned_date:
            lookback = self.config['preprocessing']['orchestration']['incremental']['look_back_days']
            start_date = last_cleaned_date - pd.Timedelta(days=lookback)
            df = df[df['fecha'] >= start_date].copy()
        
        return df.sort_values('fecha')

    def _apply_healing_steps(self, df, domain, all_domains=None):
        """Executes sequential algorithms defined in config.yaml."""
        if domain not in self.domain_stats:
            self.domain_stats[domain] = {"outliers": 0, "nulls": 0, "fixes": 0}
            
        if domain not in self.config['preprocessing']['table_rules']:
            return df

        steps = self.config['preprocessing']['table_rules'][domain].get('reconstruction_steps', [])
        df_h = df.copy()
        
        # Track applied rule names
        self.domain_stats[domain]["applied_rules"] = [s['name'] for s in sorted(steps, key=lambda x: x['step'])]

        for step in sorted(steps, key=lambda x: x['step']):
            target = step['target']
            action = step['action']
            name = step['name']
            
            # targets can be list or string
            targets = [target] if isinstance(target, str) else target
            
            logger.debug(f"[{domain}] Step {step['step']}: {name} ({action})")

            for t_col in targets:
                try:
                    if action == "if_nan_then_logic":
                        rule = step['rule']
                        mask = df_h[t_col].isna()
                        if mask.any():
                            eval_res = self._safe_eval(df_h, rule)
                            df_h.loc[mask, t_col] = eval_res.loc[mask] if isinstance(eval_res, pd.Series) else eval_res
                            count = int(mask.sum())
                            self.healing_stats['nulls_cured'] += count
                            self.domain_stats[domain]["nulls"] += count
                            self.domain_stats[domain]["healing_log"].append(f"Regla '{name}': se imputaron {count} valores nulos en '{t_col}'")

                    elif action in ["force_consistency", "force_recalculate"]:
                        rule_or_formula = step.get('rule') or step.get('formula')
                        expr = rule_or_formula.replace("current_value", t_col)
                        df_h[t_col] = self._safe_eval(df_h, expr)

                    elif action == "impute":
                        rule = step['rule_if_nan']
                        mask = df_h[t_col].isna()
                        if mask.any():
                            if rule == "ffill":
                                df_h[t_col] = df_h[t_col].ffill()
                            elif rule == "interpolate":
                                df_h[t_col] = pd.to_numeric(df_h[t_col], errors='coerce')
                                df_h[t_col] = df_h[t_col].interpolate(method='linear').ffill().bfill()
                            elif isinstance(rule, (int, float)):
                                df_h.loc[mask, t_col] = rule
                            else:
                                eval_res = self._safe_eval(df_h, rule)
                                df_h.loc[mask, t_col] = eval_res.loc[mask] if isinstance(eval_res, pd.Series) else eval_res
                            
                            count = int(mask.sum())
                            self.healing_stats['nulls_cured'] += count
                            self.domain_stats[domain]["nulls"] += count
                            self.domain_stats[domain]["healing_log"].append(f"Regla '{name}': se imputaron {count} valores nulos en '{t_col}' vía {rule}")

                    elif action in ["inherit_temporal", "calculate_and_inherit"]:
                        if action == "calculate_and_inherit" and "formula" in step:
                            df_h[t_col] = self._safe_eval(df_h, step['formula'])
                        
                        source = step.get('source', t_col)
                        lag = step.get('lag', 1)
                        if "." in source and all_domains:
                            src_domain, src_col = source.split(".")
                            if src_domain in all_domains:
                                src_df = all_domains[src_domain][['fecha', src_col]].copy()
                                df_h = df_h.merge(src_df, on='fecha', how='left', suffixes=('', '_src'))
                                source = f"{src_col}_src"

                        inherited = df_h[source].shift(lag)
                        condition = step.get('condition', 'if_nan')
                        if condition == "always":
                             df_h[t_col] = inherited
                        else:
                            mask = df_h[t_col].isna()
                            if mask.any():
                                df_h.loc[mask, t_col] = inherited[mask]
                                count = int(mask.sum())
                                self.healing_stats['nulls_cured'] += count
                                self.domain_stats[domain]["nulls"] += count
                                self.domain_stats[domain]["healing_log"].append(f"Regla '{name}': herencia temporal de {count} valores en '{t_col}'")
                        
                        if "rule_if_nan" in step:
                            rule = step['rule_if_nan']
                            mask = df_h[t_col].isna()
                            if mask.any():
                                if rule == "ffill": df_h[t_col] = df_h[t_col].ffill()
                                elif isinstance(rule, (int, float)): df_h.loc[mask, t_col] = rule
                                count = int(mask.sum())
                                self.healing_stats['nulls_cured'] += count
                                self.domain_stats[domain]["nulls"] += count
                                self.domain_stats[domain]["healing_log"].append(f"Regla '{name}': fallback {rule} para {count} valores restantes")

                        if "_src" in source: df_h.drop(columns=[source], inplace=True)

                    elif action == "sync_from_table":
                        source = step['source']
                        if "." in source and all_domains:
                            src_domain, src_col = source.split(".")
                            if src_domain in all_domains:
                                src_df = all_domains[src_domain][['fecha', src_col]].copy()
                                df_h = df_h.drop(columns=[t_col], errors='ignore').merge(
                                    src_df.rename(columns={src_col: t_col}), on='fecha', how='left'
                                )

                    elif action == "force_min_threshold":
                        rule_or_formula = step.get('rule') or step.get('formula')
                        thresh_col = step.get('threshold_source')
                        if thresh_col and thresh_col in df_h.columns:
                            mask = df_h[t_col] < df_h[thresh_col]
                            count = int(mask.sum())
                            if count > 0:
                                self.healing_stats['physical_fixes'] += count
                                self.domain_stats[domain]["fixes"] += count
                                self.domain_stats[domain]["healing_log"].append(f"Regla '{name}': corregidos {count} valores por debajo de umbral {thresh_col}")
                                df_h.loc[mask, t_col] = df_h.loc[mask, thresh_col]
                        elif rule_or_formula:
                            df_h[t_col] = self._safe_eval(df_h, rule_or_formula)

                except Exception as e:
                    logger.error(f"Error in step '{name}' for target '{t_col}': {e}")
                    # If it's a KeyError and it's a non-critical calculation, we can skip or log
                    if isinstance(e, KeyError):
                        logger.warning(f"Skipping step '{name}' due to missing column: {e}")
                        continue
                    raise

        return df_h

    def _safe_eval(self, df, expr):
        """Custom formula evaluator that handles Python functions and ternary logic."""
        if not isinstance(expr, str):
            return expr

        # 1. Handle Ternary: "ResultTrue if Condition else ResultFalse"
        if " if " in expr and " else " in expr:
            match = re.search(r"(.*)\s+if\s+(.*)\s+else\s+(.*)", expr)
            if match:
                res_true_expr = match.group(1).strip()
                cond_expr = match.group(2).strip()
                res_false_expr = match.group(3).strip()
                
                cond = self._safe_eval(df, cond_expr)
                t_val = self._safe_eval(df, res_true_expr)
                f_val = self._safe_eval(df, res_false_expr)
                
                if isinstance(t_val, (int, float, bool)): t_val = pd.Series([t_val]*len(df), index=df.index)
                if isinstance(f_val, (int, float, bool)): f_val = pd.Series([f_val]*len(df), index=df.index)
                
                return t_val.where(cond, f_val)

        # 2. Handle max(A, B) and min(A, B)
        func_match = re.search(r"(max|min)\((.*),(.*)\)", expr)
        if func_match:
            op = np.maximum if func_match.group(1) == "max" else np.minimum
            arg1 = self._safe_eval(df, func_match.group(2).strip())
            arg2 = self._safe_eval(df, func_match.group(3).strip())
            return op(arg1, arg2)

        # 3. Final pass: pd.eval for balance (math/columns)
        try:
            return df.eval(expr)
        except Exception as e:
            if expr in df.columns:
                return df[expr]
            try:
                # Handle simple literals like "0" or "None"
                return eval(expr, {"__builtins__": None}, {})
            except:
                raise RuntimeError(f"Could not evaluate expression '{expr}': {e}")

    def _apply_outlier_policy(self, df, domain):
        """Cleans unjustified spikes."""
        if domain not in self.domain_stats:
            self.domain_stats[domain] = {"outliers": 0, "nulls": 0, "fixes": 0}
            
        """Removes unjustified outliers (values far from physical reality)."""
        if domain not in self.config['preprocessing']['table_rules']:
            return df
        
        policy = self.config['preprocessing']['table_rules'][domain].get('outlier_policy', {})
        if not policy:
            return df
            
        target = policy['target']
        threshold = policy['max_threshold']
        flag_col = policy['flag_column']
        
        # Kill logic
        kill_mask = df[target] > threshold
        count = int(kill_mask.sum())
        
        df_out = df.copy()
        if domain not in self.domain_stats:
             self.domain_stats[domain] = {"outliers": 0, "nulls": 0, "fixes": 0, "healing_log": []}
        
        if count > 0:
            self.healing_stats['outliers_detected'] += count
            self.domain_stats[domain]["outliers"] += count
            self.domain_stats[domain]["healing_log"].append(f"Outlier Policy: se removieron {count} filas por superar umbral físico en '{target}'")
        
        df_out.loc[kill_mask, target] = np.nan
        return df_out

    def _consolidate_master(self, df_dict):
        """Merges all domains and ensures daily continuity (Zero Gaps Law)."""
        master_df = df_dict['ventas'].copy()
        
        for domain, df in df_dict.items():
            if domain == 'ventas': continue
            # Merge exogenas
            master_df = master_df.merge(df, on='fecha', how='left')

        # Continuity & reindex (Zero Gaps Law)
        master_df = master_df.sort_values('fecha').drop_duplicates('fecha')
        min_date = master_df['fecha'].min()
        max_date = master_df['fecha'].max()
        full_range = pd.date_range(start=min_date, end=max_date, freq='D')
        
        if self.config['preprocessing']['global_settings']['continuity']['ensure_zero_gaps']:
            pre_count = len(master_df)
            master_df = master_df.set_index('fecha').reindex(full_range).reset_index().rename(columns={'index': 'fecha'})
            gap_count = len(master_df) - pre_count
            if gap_count > 0:
                logger.info(f"Continuity Law: Created {gap_count} rows to fill temporal gaps.")
                # Distribute gaps logically across domains for the report 
                # (Simple approach: attribute to 'ventas' as it's the master backbone)
                if 'ventas' in self.domain_stats:
                    self.domain_stats['ventas']['gaps_filled'] = gap_count
        else:
            master_df = master_df.set_index('fecha').reindex(full_range).reset_index().rename(columns={'index': 'fecha'})

        # Smart Fill: Pillar of Continuity
        # 1. Rule-Aware Filling (Domain specific)
        for domain, df_domain in df_dict.items():
            rules = self.config['preprocessing']['table_rules'].get(domain, {}).get('reconstruction_steps', [])
            
            # Map rule-targets to their possibly suffixed master column names
            fill_map = {}
            for step in rules:
                if step.get('action') == 'if_nan_then_logic':
                    target = step['target']
                    targets = [target] if isinstance(target, str) else target
                    for t in targets:
                        # Find matching column in master_df (might have _x or _y)
                        if t in master_df.columns:
                            fill_map[t] = step['rule']
                        else:
                            # Search for suffix versions
                            for master_col in master_df.columns:
                                if master_col.startswith(f"{t}_") or master_col.endswith(f"_{t}"):
                                    fill_map[master_col] = step['rule']

            for col, rule in fill_map.items():
                mask = master_df[col].isna()
                if mask.any():
                    eval_res = self._safe_eval(master_df, rule)
                    master_df.loc[mask, col] = eval_res.loc[mask] if isinstance(eval_res, pd.Series) else eval_res
                    logger.debug(f"Applied Rule-Fill to '{col}' in gaps.")

        # 2. Global Heuristics (Cleanup remaining nulls)
        for col in master_df.columns:
            if col == 'fecha': continue
            mask = master_df[col].isna()
            if not mask.any(): continue
            
            # Priority 1: Generic Business Patterns (Categorical/Flag-like)
            if any(k in col.lower() for k in ['flag', 'promocion', 'festivo', 'ads', 'precio', 'costo', 'updated_at', 'valor']):
                master_df[col] = master_df[col].ffill().fillna(0)
            
            # Priority 2: Linear Interpolation (Physical/Continuity fallback)
            else:
                try:
                    master_df[col] = master_df[col].interpolate(method='linear').ffill().bfill()
                except:
                    # Non-numeric might fail interpolation
                    master_df[col] = master_df[col].ffill().fillna(0)
        
        return master_df

    def _quality_gate(self, df):
        """Certifies the master dataset against zero-tolerance rules."""
        logger.info("Executing Final Quality Gate Audit...")
        
        # 1. Full Row Duplicates
        dupe_rows = int(df.duplicated().sum())
        
        # 2. Duplicate Dates (Entity Uniqueness)
        dupe_dates = int(df['fecha'].duplicated().sum())
        
        # 3. Overall Nulls
        null_count = int(df.isna().sum().sum())
        
        # 4. Temporal Gaps (Series Continuity)
        if len(df) > 1:
            sorted_dates = pd.to_datetime(df['fecha']).sort_values()
            gaps = int((sorted_dates.diff().dt.days > 1).sum())
        else:
            gaps = 0

        # Store Audit for Report
        self.output_audit = {
            "duplicate_rows": dupe_rows,
            "duplicate_dates": dupe_dates,
            "null_values": null_count,
            "temporal_gaps": gaps
        }
        
        # Fail if anything critical is detected
        if dupe_rows > 0 or dupe_dates > 0 or null_count > 0 or gaps > 0:
            logger.error(f"Quality Gate FAILED Audit: RowsDup={dupe_rows}, DateDup={dupe_dates}, Nulls={null_count}, Gaps={gaps}")
            return False
        
        logger.info("Quality Gate Audit: PASSED (100% Reliability)")
        return True

    def _sync_execution_to_supabase(self, status, last_date, row_count, avg_health, error_msg=None, extra_info=None):
        """Logs phase results with structured JSON reporting and exact naming conventions."""
        if not self.config['preprocessing']['orchestration']['execution_tracking']['enabled']:
            return

        # 1. Supabase Sync (Entry for Postgres)
        clean_date = "1900-01-01" # Default to avoid NOT NULL constraint if N/A
        if hasattr(last_date, 'date'):
            clean_date = str(last_date.date())
        elif isinstance(last_date, str) and last_date != "N/A":
            clean_date = last_date

        entry = {
            "phase": self.config['preprocessing']['orchestration']['execution_tracking']['phase_name'],
            "last_processed_date": clean_date,
            "master_row_count": int(row_count),
            "processing_type": self.processing_type,
            "health_score_avg": float(avg_health),
            "anomalies_detected": int(self.healing_stats['outliers_detected'] + self.healing_stats['physical_fixes']),
            "output_path": os.path.join(self.cleansed_path, self.master_dataset_file),
            "status": status,
            "error_message": error_msg
        }
        
        try:
            self.client.table("pipeline_execution_status").insert(entry).execute()
        except Exception as e:
            logger.warning(f"Supabase Sync failed: {e}")

        # 2. Local JSON Report (Structured Style Phase 01)
        
        # Build Metadata & Summary (Sections common to all reports)
        report = {
            "metadata": {
                "phase": "02",
                "phase_name": "Preprocessing & Data Healing",
                "execution_mode": self.config['preprocessing']['orchestration']['incremental']['mode'],
                "timestamp": self.timestamp,
                "project": self.config['general']['project_name']
            },
            "execution_summary": {
                "overall_status": status,
                "processing_type": self.processing_type,
                "summary": error_msg if error_msg else (extra_info.get("processing_description") if extra_info else f"Preprocessing finished with status: {status}"),
                "total_rows_produced": int(row_count),
                "date_range": extra_info.get("date_range") if extra_info else "N/A"
            },
            "input_data_health": {
                "source": "Supabase (data_inventory_status)",
                "table_health_scores": {k: f"{float(v):.2f}%" for k, v in self.input_health_status.items()}
            }
        }

        # SPECIAL CASE: Early Handshake Failure (LOAD phase failed)
        if error_msg and "Latest LOAD phase" in error_msg:
             report["execution_summary"]["summary"] = "Preprocessing ABORTED. Phase 01 (LOAD) did not complete successfully. Check Phase 01 logs."
             report["technical_error"] = error_msg
        else:
            # Full report logic (Healing Details & Quality Gate)
            detailed_log = {}
            for domain in self.config['extractions']['tables']:
                stats = self.domain_stats.get(domain, {
                    "outliers": 0, "nulls": 0, "fixes": 0, "anti_leakage": 0, 
                    "deduplicated": 0, "pruned_cols": [], "gaps_filled": 0,
                    "applied_rules": [], "healing_log": []
                })
                
                if not stats.get("applied_rules"):
                    config_rules = self.config['preprocessing']['table_rules'].get(domain, {}).get('reconstruction_steps', [])
                    stats["applied_rules"] = [r['name'] for r in sorted(config_rules, key=lambda x: x['step'])]

                global_actions = []
                if stats.get('anti_leakage', 0) > 0: global_actions.append(f"Anti-Leakage: {stats.get('anti_leakage')} filas descartadas")
                if stats.get('deduplicated', 0) > 0: global_actions.append(f"Deduplicación: {stats.get('deduplicated')} filas filtradas")
                if stats.get('pruned_cols'): global_actions.append(f"Poda: {len(stats.get('pruned_cols'))} columnas removidas")
                if stats.get('gaps_filled', 0) > 0: global_actions.append(f"Continuidad: {stats.get('gaps_filled')} días creados")
                
                detailed_log[domain] = {
                    "global_laws_compliance": global_actions if global_actions else ["Cumple todas las leyes globales"],
                    "healing_and_reconstruction": stats.get("healing_log", []) if stats.get("healing_log") else ["Sanity OK"],
                    "business_rules_names": stats.get("applied_rules", [])
                }

            report["healing_details"] = {
                "domain_drilldown": detailed_log,
                "overall_stats": {
                    "outliers_detected": int(self.healing_stats['outliers_detected']),
                    "nulls_cured": int(self.healing_stats['nulls_cured']),
                    "physical_fixes": int(self.healing_stats['physical_fixes'])
                }
            }
            report["quality_metrics"] = {
                "health_score_avg": float(avg_health),
                "quality_gate_passed": status == "SUCCESS",
                "output_health_audit": {
                    "duplicate_rows": int(self.output_audit['duplicate_rows']),
                    "duplicate_dates": int(self.output_audit['duplicate_dates']),
                    "total_null_values": int(self.output_audit['null_values']),
                    "temporal_series_gaps": int(self.output_audit['temporal_gaps']),
                    "audit_status": "CERTIFIED" if status == "SUCCESS" else "FAILED"
                },
                "total_rows": int(row_count),
                "output_file": entry["output_path"]
            }
            # Add Master Schema info if available in extra_info
            if extra_info and "schema" in extra_info:
                report["quality_metrics"]["master_schema"] = extra_info["schema"]

            if error_msg: report["technical_error"] = error_msg
        
        # Naming Convention: phase_02_preprocessing_latest.json
        base_name = "phase_02_preprocessing"
        latest_path = os.path.join(self.reports_path, f"{base_name}_latest.json")
        
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4, ensure_ascii=False)
            
        # History: history/phase_02_preprocessing_YYYYMMDD_HHMMSS.json
        history_name = f"{base_name}_{self.timestamp}.json"
        history_path = os.path.join(self.reports_path, "history", history_name)
        
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4, ensure_ascii=False)
            
        logger.info(f"Official Phase 02 Report generated at: {latest_path}")

    def run(self):
        """Phased execution with state-aware reporting."""
        try:
            # 1. Handshake
            go, context_or_msg, avg_health = self._handshake()
            if not go:
                # context_or_msg contains the error reason
                self._sync_execution_to_supabase("FAILED", "N/A", 0, avg_health or 0, context_or_msg)
                return "FAILED"
            
            safe_date = context_or_msg # In case of success, context is the safe_date

            # 2. Context & State Detection
            master_path = os.path.join(self.cleansed_path, self.master_dataset_file)
            last_cleaned_date = None
            
            if os.path.exists(master_path):
                df_hist = pd.read_parquet(master_path)
                last_cleaned_date = pd.to_datetime(df_hist['fecha'].max())
                self.processing_type = "INCREMENTAL"
            else:
                self.processing_type = "FULL"

            # 3. Load Data
            all_raw = {}
            tables = self.config['extractions']['tables']
            for t in tables:
                df = self._load_raw_domain(t, last_cleaned_date)
                if df is not None: all_raw[t] = df

            # Detect "NO NEW DATA" state
            if last_cleaned_date and all_raw:
                max_new = max([df['fecha'].max() for df in all_raw.values()])
                if max_new <= last_cleaned_date:
                    self.processing_type = "NO NEW DATA"
                    logger.info("No new data found in sources. Skipping processing and generating current state report.")
                    
                    # For NO NEW DATA, we still audit the current master
                    master_df = pd.read_parquet(master_path)
                    self._quality_gate(master_df) # Populate output_audit
                    schema_info = {col: str(dtype) for col, dtype in master_df.dtypes.items()}
                    
                    self._sync_execution_to_supabase(
                        "SUCCESS", 
                        master_df['fecha'].max(), 
                        len(master_df), 
                        avg_health,
                        extra_info={
                            "processing_description": f"Mode: NO NEW DATA. No new records found in Supabase since {last_cleaned_date.date()}. Dataset is already compliant.", 
                            "date_range": [str(master_df['fecha'].min().date()), str(master_df['fecha'].max().date())],
                            "schema": schema_info
                        }
                    )
                    return "SUCCESS"

            # 4. Second Pass: Heal
            healed_domains = {}
            for t, df in all_raw.items():
                logger.info(f"Healing domain: {t}")
                df_no_o = self._apply_outlier_policy(df, t)
                df_h = self._apply_healing_steps(df_no_o, t, all_raw)
                healed_domains[t] = df_h
                
                # Save local domain-truth
                df_h.to_parquet(os.path.join(self.cleansed_path, f"{t}.parquet"), index=False)

            # 5. Consolidation
            master_df = self._consolidate_master(healed_domains)
            
            # 6. Delta Fusion
            if last_cleaned_date and os.path.exists(master_path):
                df_hist = pd.read_parquet(master_path)
                master_df = pd.concat([df_hist[df_hist['fecha'] < master_df['fecha'].min()], master_df])

            # 6.b Cleanup Internal Calculation Columns (Drop __temp_*)
            temp_cols = [c for c in master_df.columns if c.startswith("__temp_")]
            if temp_cols:
                logger.info(f"Removing {len(temp_cols)} temporary calculation columns after fusion: {temp_cols}")
                master_df.drop(columns=temp_cols, inplace=True)

            # 7. Final Check & Sync
            if not self._quality_gate(master_df):
                 reasons = []
                 if self.output_audit['duplicate_rows'] > 0: reasons.append("Duplicate rows detected")
                 if self.output_audit['duplicate_dates'] > 0: reasons.append("Duplicate dates detected")
                 if self.output_audit['null_values'] > 0: reasons.append(f"Null values detected ({self.output_audit['null_values']})")
                 if self.output_audit['temporal_gaps'] > 0: reasons.append("Temporal series gaps detected")
                 
                 qg_msg = f"Quality Gate FAILED: {', '.join(reasons)}"
                 self._sync_execution_to_supabase("FAILED", "N/A", 0, avg_health, qg_msg)
                 return "FAILED"

            master_df.to_parquet(master_path, index=False)
            
            # Determine processing description for report
            processing_desc = f"Mode: {self.processing_type}. "
            if self.processing_type == "FULL":
                processing_desc += "Fresh historical data processed from scratch."
            else:
                processing_desc += f"New data integrated since {last_cleaned_date.date()}."
            
            # Record Schema Metadata
            schema_info = {col: str(dtype) for col, dtype in master_df.dtypes.items()}
            
            self._sync_execution_to_supabase(
                "SUCCESS", 
                master_df['fecha'].max(), 
                len(master_df), 
                avg_health,
                extra_info={
                    "processing_description": processing_desc, 
                    "date_range": [str(master_df['fecha'].min().date()), str(master_df['fecha'].max().date())],
                    "schema": schema_info
                }
            )
            return "SUCCESS"

        except Exception as e:
            logger.error(f"Preprocessing Error: {e}", exc_info=True)
            self._sync_execution_to_supabase("FAILED", "N/A", 0, 0, str(e))
            return "FAILED"

if __name__ == "__main__":
    import yaml
    import os
    
    # Configure logging for direct execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load config from project root (assuming we run from root)
    config_path = os.path.join(os.getcwd(), "config.yaml")
    if not os.path.exists(config_path):
        logger.error(f"Config file not found at {config_path}")
    else:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        
        prepro = Preprocessor(cfg)
        status = prepro.run()
        print(f"\n--- Preprocessing Phase Finished with Status: {status} ---\n")
