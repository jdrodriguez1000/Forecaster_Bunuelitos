import os
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
        self.master_dataset_file = self.config['preprocessing']['orchestration']['incremental']['master_file']
        self.reports_path = os.path.join(self.config['general']['outputs_path'], "reports", "phase_02")
        
        # Ensure directories exist
        os.makedirs(self.cleansed_path, exist_ok=True)
        os.makedirs(self.reports_path, exist_ok=True)
        os.makedirs(os.path.join(self.reports_path, "history"), exist_ok=True)
        
        # Internal state
        self.healing_stats = {
            "outliers_detected": 0,
            "nulls_cured": 0,
            "physical_fixes": 0
        }

    def _handshake(self):
        """Validates if we can start preprocessing based on Phase 01 status."""
        logger.info("Performing Preprocessing Handshake (Go/No-Go)...")
        handshake_cfg = self.config['preprocessing']['orchestration']['handshake']
        tables_to_check = handshake_cfg['tables_to_check']
        required_status = handshake_cfg['required_status']
        min_health_score = handshake_cfg['min_health_score']

        res = self.client.table("data_inventory_status").select("*").in_("table_name", tables_to_check).execute()
        
        if not res.data:
            raise RuntimeError("Handshake failed: No inventory status found in Supabase.")

        status_df = pd.DataFrame(res.data)
        
        failed_tables = status_df[status_df['status'] != required_status]['table_name'].tolist()
        if failed_tables:
            logger.error(f"Handshake FAILED. Tables not ready: {failed_tables}")
            return False, None, None

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
        """Loads and filters raw data."""
        raw_file = os.path.join(self.raw_path, f"{domain}.parquet")
        if not os.path.exists(raw_file):
            return None

        df = pd.read_parquet(raw_file)
        df['fecha'] = pd.to_datetime(df['fecha'])
        
        if last_cleaned_date:
            lookback = self.config['preprocessing']['orchestration']['incremental']['look_back_days']
            start_date = last_cleaned_date - pd.Timedelta(days=lookback)
            df = df[df['fecha'] >= start_date].copy()
        
        return df.sort_values('fecha')

    def _apply_healing_steps(self, df, domain, all_domains=None):
        """Executes sequential algorithms defined in config.yaml."""
        if domain not in self.config['preprocessing']['table_rules']:
            return df

        steps = self.config['preprocessing']['table_rules'][domain].get('reconstruction_steps', [])
        df_h = df.copy()

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
                            self.healing_stats['nulls_cured'] += mask.sum()

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
                            df_h.loc[mask, t_col] = inherited[mask]
                        
                        if "rule_if_nan" in step:
                            rule = step['rule_if_nan']
                            mask = df_h[t_col].isna()
                            if rule == "ffill": df_h[t_col] = df_h[t_col].ffill()
                            elif isinstance(rule, (int, float)): df_h.loc[mask, t_col] = rule

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
                            self.healing_stats['physical_fixes'] += mask.sum()
                            df_h.loc[mask, t_col] = df_h.loc[mask, thresh_col]
                        elif rule_or_formula:
                            df_h[t_col] = self._safe_eval(df_h, rule_or_formula)

                except Exception as e:
                    logger.error(f"Error in step '{name}' for target '{t_col}': {e}")
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

    def _apply_outlier_policy(self, df):
        """Cleans unjustified spikes."""
        if not self.config['preprocessing']['outlier_policy']['enabled']:
            return df
        
        df_out = df.copy()
        policy = self.config['preprocessing']['outlier_policy']
        flag_col = policy['flag_column']
        target = self.config['general']['target_variable']

        if flag_col not in df_out.columns or target not in df_out.columns:
            return df_out

        triggers = policy['business_success']['justification_triggers']
        # An outlier is JUSTIFIED if ANY trigger is 1
        justification_mask = pd.Series([False] * len(df_out))
        for t in triggers:
            if t in df_out.columns:
                justification_mask |= (df_out[t] == 1)
        
        # Kill unjustified outliers
        kill_mask = (df_out[flag_col] == 1) & ~justification_mask
        self.healing_stats['outliers_detected'] += kill_mask.sum()
        df_out.loc[kill_mask, target] = np.nan
        df_out.loc[kill_mask, flag_col] = 0
            
        return df_out

    def _consolidate_master(self, df_dict):
        """Merges all domains and ensures daily continuity."""
        master_df = df_dict['ventas'].copy()
        
        for domain, df in df_dict.items():
            if domain == 'ventas': continue
            # Merge exogenas
            master_df = master_df.merge(df, on='fecha', how='left')

        # Continuity & reindex
        master_df = master_df.sort_values('fecha').drop_duplicates('fecha')
        full_range = pd.date_range(start=master_df['fecha'].min(), end=master_df['fecha'].max(), freq='D')
        master_df = master_df.set_index('fecha').reindex(full_range).reset_index().rename(columns={'index': 'fecha'})
        
        # Smart Fill
        for col in master_df.columns:
            if col == 'fecha': continue
            if any(k in col for k in ['flag', 'promocion', 'festivo', 'ads', 'precio', 'costo']):
                master_df[col] = master_df[col].ffill().fillna(0)
            else:
                master_df[col] = master_df[col].interpolate(method='linear').ffill().bfill()

        return master_df

    def _quality_gate(self, df):
        """Primacy check."""
        logger.info("Executing Final Quality Gate...")
        nans = df.isna().sum().sum()
        dupes = df['fecha'].duplicated().sum()
        
        if nans > 0 or dupes > 0:
            logger.error(f"Quality Gate FAILED: NaNs={nans}, Dupes={dupes}")
            return False
        
        logger.info("Quality Gate PASSED.")
        return True

    def _sync_execution_to_supabase(self, status, last_date, row_count, avg_health, error_msg=None):
        """Logs phase results."""
        if not self.config['preprocessing']['orchestration']['execution_tracking']['enabled']:
            return

        # Ensure date is valid for Postgres format
        clean_date = None
        if hasattr(last_date, 'date'):
            clean_date = str(last_date.date())
        elif isinstance(last_date, str) and last_date != "N/A":
            clean_date = last_date

        # Standardize numeric types for JSON serialization (Pandas results include int64/float64)
        entry = {
            "phase": self.config['preprocessing']['orchestration']['execution_tracking']['phase_name'],
            "last_processed_date": clean_date,
            "master_row_count": int(row_count),
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

        # 2. Local JSON Report (Wow Factor / Dual Persistence)
        report = {
            "metadata": {
                "execution_id": f"PP_{self.timestamp}",
                "timestamp": datetime.now().isoformat(),
                "phase": "PREPROCESSING",
                "mode": self.config['preprocessing']['orchestration']['incremental']['mode'],
                "project": self.config['general']['project_name']
            },
            "results": entry,
            "technical_details": {
                "input_tables": self.config['extractions']['tables'],
                "healing_breakdown": {k: int(v) for k, v in self.healing_stats.items()}
            }
        }
        
        # Save Latest
        latest_path = os.path.join(self.reports_path, "report_latest.json")
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4, ensure_ascii=False)
            
        # Save History
        history_path = os.path.join(self.reports_path, "history", f"report_{self.timestamp}.json")
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4, ensure_ascii=False)
            
        logger.info(f"Local Executive Report generated at: {latest_path}")

    def run(self):
        """Phased execution."""
        try:
            # 1. Handshake
            go, safe_date, avg_health = self._handshake()
            if not go: return "FAILED"

            # 2. Context
            last_cleaned_date = self._get_delta_context() if self.config['preprocessing']['orchestration']['incremental']['mode'] == "delta" else None
            
            # 3. First Pass: Load all (needed for cross-domain syncs like sync_from_table)
            all_raw = {}
            tables = self.config['extractions']['tables']
            for t in tables:
                df = self._load_raw_domain(t, last_cleaned_date)
                if df is not None: all_raw[t] = df

            # 4. Second Pass: Heal
            healed_domains = {}
            for t, df in all_raw.items():
                logger.info(f"Healing domain: {t}")
                df_no_o = self._apply_outlier_policy(df)
                df_h = self._apply_healing_steps(df_no_o, t, all_raw)
                healed_domains[t] = df_h
                # Save local domain-truth
                df_h.to_parquet(os.path.join(self.cleansed_path, f"{t}.parquet"), index=False)

            # 5. Consolidation
            master_df = self._consolidate_master(healed_domains)
            
            # 6. Delta Fusion
            master_path = os.path.join(self.cleansed_path, self.master_dataset_file)
            if last_cleaned_date and os.path.exists(master_path):
                df_hist = pd.read_parquet(master_path)
                master_df = pd.concat([df_hist[df_hist['fecha'] < master_df['fecha'].min()], master_df])

            # 7. Final Check & Sync
            if not self._quality_gate(master_df): return "FAILED"

            master_df.to_parquet(master_path, index=False)
            self._sync_execution_to_supabase("SUCCESS", master_df['fecha'].max(), len(master_df), avg_health)
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
