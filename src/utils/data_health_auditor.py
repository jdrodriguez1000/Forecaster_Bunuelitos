import os
import json
import yaml
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from src.utils.business_rules_engine import BusinessRulesEngine

class DataHealthAuditor:
    """
    Data Governance Auditor v2.3
    Implements 4 Pillars of Governance with explicit reporting of:
    - Sentinel Values
    - Duplicate Rows
    - Duplicate Dates
    - Data Types & Schema
    - Mass & Sync
    - Leakage & Cross-Validation
    - Drift & Business Rules
    """
    
    # Internal white list to avoid false positives in Schema Drift
    SYSTEM_COLUMNS = ['day', 'month', 'year', 'is_holiday', 'is_weekend']

    def __init__(self, contract_path, snapshot_path, reference_date=None):
        self.contract_path = contract_path
        self.snapshot_path = snapshot_path
        self.reference_date = reference_date if reference_date else date.today()
        self.contract = self._load_data(contract_path, "yaml")
        self.snapshot = self._load_data(snapshot_path, "json")
        self.rules_engine = BusinessRulesEngine()
        self.dataframes = {}
        self.report = {
            "metadata": {
                "phase": "01",
                "phase_name": "Data Loading & Validation",
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
            },
            "summary": {
                "total_tables": 0,
                "total_violations": 0,
                "failure_count": 0,
                "warning_count": 0,
                "status": "SUCCESS",
                "health_score": 100,
                "pillars": {
                    "pilar_1": {"status": "SUCCESS", "violations_count": 0, "passed_checks_count": 0},
                    "pilar_2": {"status": "SUCCESS", "violations_count": 0, "passed_checks_count": 0},
                    "pilar_3": {"status": "SUCCESS", "violations_count": 0, "passed_checks_count": 0},
                    "pilar_4": {"status": "SUCCESS", "violations_count": 0, "passed_checks_count": 0}
                }
            },
            "tables": {}
        }
        self.SYSTEM_COLUMNS = ['updated_at', 'id']

    def _load_data(self, input_path, file_type):
        if not isinstance(input_path, str): return input_path
        with open(input_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) if file_type == "yaml" else json.load(f)

    def audit_dataframe(self, table_name, df, horizon_days=185):
        if table_name not in self.contract['tables']: return
        self.dataframes[table_name] = df 

        table_report = {
            "status": "SUCCESS",
            "violations": [],
            "passed_checks": [],
            "pillars": {
                "pilar_1": {"status": "SUCCESS", "violations": [], "passed_checks": []},
                "pilar_2": {"status": "SUCCESS", "violations": [], "passed_checks": []},
                "pilar_3": {"status": "SUCCESS", "violations": [], "passed_checks": []},
                "pilar_4": {"status": "SUCCESS", "violations": [], "passed_checks": []}
            },
            "stats": {
                "row_count": len(df),
                "null_pct": float(df[[c for c in df.columns if not c.startswith("__temp_")]].isnull().mean().mean()) if not df.empty else 0.0,
                "integrity_metrics": {
                    "duplicate_rows": 0,
                    "duplicate_dates": 0,
                    "sentinel_hits": 0
                },
                "statistical_profiling": {
                    "high_cardinality_cols": [],
                    "zero_variance_cols": [],
                    "high_zero_pct_cols": []
                }
            }
        }

        # 1. Structural, Process and Statistics (Pure data from source)
        self._audit_pilar_1(table_name, df, table_report)
        self._audit_pilar_2(table_name, df, table_report)
        self._audit_pilar_3(table_name, df, table_report)
        
        # 2. Domain Logic (Last step - May create/clean technical temp columns)
        self._audit_pilar_4(table_name, df, table_report)

        self._consolidate_table_report(table_report)
        self.report['tables'][table_name] = table_report
        return table_report

    def _audit_pilar_1(self, table_name, df, table_report):
        """Structural Integrity (Pillar 1)."""
        table_contract = self.contract['tables'][table_name]
        contract_cols = table_contract.get('columns', {})
        data_cols = set(df.columns)
        
        # 1. Schema & Extra Columns
        missing = list(set(contract_cols.keys()) - data_cols)
        if missing:
            self._add_violation(table_report, "pilar_1", "FAILURE", f"Columnas ausentes: {missing}")
        else:
            self._add_passed_check(table_report, "pilar_1", "Esquema completo (todas las columnas presentes).")

        # Filter out authorized system columns AND hidden technical temp columns (__temp_*)
        extra = [c for c in (data_cols - set(contract_cols.keys())) 
                 if c not in self.SYSTEM_COLUMNS and not c.startswith("__temp_")]
        if extra:
            self._add_violation(table_report, "pilar_1", "WARNING", f"Schema Drift (Columnas extra): {extra}")
        else:
            self._add_passed_check(table_report, "pilar_1", "Esquema fiel (sin columnas extra no autorizadas).")

        # 2. Data Types & Schema Quality
        type_issues = False
        for col, rules in contract_cols.items():
            if col not in df.columns: continue
            expected_type = rules.get('type', 'any')
            actual_dtype = str(df[col].dtype)
            match = True
            
            # Smart Type Matching
            if expected_type == 'int' and not ('int' in actual_dtype): match = False
            elif expected_type == 'float' and not (('float' in actual_dtype) or ('int' in actual_dtype)): 
                # Accept ints as floats (auto-upcast)
                match = True
            elif expected_type == 'datetime' and not ('datetime' in actual_dtype or 'date' in actual_dtype): match = False
            elif expected_type == 'string' and not ('object' in actual_dtype or 'str' in actual_dtype or 'string' in actual_dtype): match = False
            
            if not match:
                self._add_violation(table_report, "pilar_1", "FAILURE", f"Validación de Tipo: '{col}' debe ser {expected_type} (Encontrado: {actual_dtype})")
                type_issues = True
        
        if not type_issues:
            self._add_passed_check(table_report, "pilar_1", "Tipos de datos certificados (Conformidad 100%).")

        # 3. Nulls & Sentinels
        max_null = self.contract.get('global_standards', {}).get('integrity_defaults', {}).get('null_management', {}).get('default_max_null_pct', 0.05)
        any_null_issue = False
        for col, rules in contract_cols.items():
            if col not in df.columns: continue
            null_pct = float(df[col].isnull().mean())
            if rules.get('required') and null_pct > 0:
                self._add_violation(table_report, "pilar_1", "FAILURE", f"Nulos en '{col}': Prohibido para campo requerido ({null_pct:.1%}).")
                any_null_issue = True
            elif null_pct > max_null:
                self._add_violation(table_report, "pilar_1", "WARNING", f"Nulos en '{col}': Excede tolerancia ({null_pct:.1%} > {max_null:.1%}).")
                any_null_issue = True
        if not any_null_issue:
            self._add_passed_check(table_report, "pilar_1", f"Higiene de nulos: OK (Tolerancia < {max_null:.0%}).")

        # Sentinel Check
        sentinel_total = 0
        sentinels = self.contract.get('global_standards', {}).get('sentinel_values', {})
        for col in df.columns:
            if col in self.SYSTEM_COLUMNS: continue
            for cat, vals in sentinels.items():
                # Filter out values that are not in the current column's data
                hits = df[col].isin(vals).sum()
                if hits > 0:
                    sentinel_total += hits
                    self._add_violation(table_report, "pilar_1", "WARNING", f"Valores Centinela en '{col}': {hits} registros encontrados ({cat}).")
        
        table_report['stats']['integrity_metrics']['sentinel_hits'] = int(sentinel_total)
        if sentinel_total == 0:
            self._add_passed_check(table_report, "pilar_1", "Control de Centinelas: 0 valores sospechosos hallados.")

    def _audit_pilar_2(self, table_name, df, table_report):
        """Process Integrity (Pillar 2)."""
        if df.empty: return
        
        # 1. Duplicate Rows
        dups = int(df.duplicated().sum())
        table_report['stats']['integrity_metrics']['duplicate_rows'] = dups
        if dups > 0:
            self._add_violation(table_report, "pilar_2", "FAILURE", f"Filas Duplicadas: Hallados {dups} registros idénticos.")
        else:
            self._add_passed_check(table_report, "pilar_2", "Integridad de registros: 0 filas duplicadas.")

        # 2. Duplicate Dates
        if 'fecha' in df.columns:
            # We use string to avoid isin issues with direct dates in some versions
            date_dups = int(df['fecha'].duplicated().sum())
            table_report['stats']['integrity_metrics']['duplicate_dates'] = date_dups
            if date_dups > 0:
                self._add_violation(table_report, "pilar_2", "FAILURE", f"Fechas Duplicadas: {date_dups} colisiones temporales en '{table_name}'.")
            else:
                self._add_passed_check(table_report, "pilar_2", "Periodicidad única: 0 fechas duplicadas.")

        # 3. Sync & Mass
        self._audit_sync_and_mass(table_name, df, table_report)

        # 4. Data Leakage (Temporal Security)
        if 'fecha' in df.columns:
            today_val = date.today()
            # Rule: No current (T) or future (>T) data allowed. Must be <= T-1.
            illegal_data = df[pd.to_datetime(df['fecha']).dt.date >= today_val]
            if not illegal_data.empty:
                max_illegal = pd.to_datetime(illegal_data['fecha']).dt.date.max()
                self._add_violation(table_report, "pilar_2", "FAILURE", 
                    f"Data Leakage: Se detectaron registros del día actual o futuro ({max_illegal}). "
                    f"El modelo solo puede ver hasta T-1 ({today_val - timedelta(days=1)}).")
            else:
                self._add_passed_check(table_report, "pilar_2", "Seguridad Temporal: Sin fuga de datos (Máximo T-1).")

        # 5. Referential integrity
        if table_name != 'ventas' and 'ventas' in self.dataframes:
            anchor_dates = set(pd.to_datetime(self.dataframes['ventas']['fecha']).dt.date)
            curr_dates = set(pd.to_datetime(df['fecha']).dt.date) if 'fecha' in df.columns else set()
            missing = curr_dates - anchor_dates
            if missing and len(curr_dates) > 0:
                self._add_violation(table_report, "pilar_2", "WARNING", f"Integridad Referencial: {len(missing)} fechas huerfanas (fuera de Ventas).")
            else:
                self._add_passed_check(table_report, "pilar_2", "Validación Cruzada: Integridad referencial OK.")

    def _audit_sync_and_mass(self, table_name, df, table_report):
        if 'fecha' not in df.columns: return
        df_dates = pd.to_datetime(df['fecha']).dt.date
        max_date = df_dates.max()
        today_val = self.reference_date
        gap = (today_val - max_date).days
        
        # 5.1 Frontera Temporal
        if gap == 1:
            self._add_passed_check(table_report, "pilar_2", f"Frontera Temporal: Al día (Última fecha permitida: {max_date}).")
        elif gap == 0:
            # This is technically leakage, but we report it here as a synchronization status too
            self._add_violation(table_report, "pilar_2", "WARNING", f"Frontera Temporal: Sobrecarga de datos. Se detectó el día actual ({max_date}), lo cual genera Leakage.")
        else:
            self._add_violation(table_report, "pilar_2", "FAILURE", f"Frontera Temporal: Brecha de {gap} días detectada (Último dato: {max_date}). Se requiere hasta {today_val - timedelta(days=1)}.")

        # 5.2 Consistencia de Masa (Volumen Proporcional)
        snap_table = self.snapshot.get('tables', {}).get(table_name, {})
        hist_rows = snap_table.get('row_count', 0)
        
        # Si faltan días (gap > 1), validamos si el volumen es proporcional
        if hist_rows > 0:
            # Aproximación de registros por día histórica
            avg_mass_daily = hist_rows / 3346 # Basado en la historia base
            days_in_current = (max_date - df_dates.min()).days + 1
            current_mass_daily = len(df) / days_in_current if days_in_current > 0 else 0
            
            # Lógica: Inconsistencia de Sincronización
            if current_mass_daily < (avg_mass_daily * 0.75):
                self._add_violation(table_report, "pilar_2", "FAILURE", 
                    f"Inconsistencia de Sincronización: El volumen de registros ({current_mass_daily:.1f}/día) no es proporcional al promedio histórico ({avg_mass_daily:.1f}/día). Posible sub-reporte.")
            else:
                self._add_passed_check(table_report, "pilar_2", f"Consistencia de Masa: Volumen proporcional ({current_mass_daily:.1f} reg/día).")

    def _audit_pilar_3(self, table_name, df, table_report):
        """Statistical Health (Pillar 3)."""
        strategy = self.contract.get('monitoring_strategy', {}).get('statistical_profiling', {})
        card_thresh = strategy.get('high_cardinality_ratio', 0.8)
        zero_pct_thresh = strategy.get('zero_pct_threshold', 0.95)
        
        stats_issues = False
        for col in df.columns:
            if col in self.SYSTEM_COLUMNS or col.startswith("__temp_"): continue
            unique_count = df[col].nunique()
            ratio = unique_count / len(df) if len(df) > 0 else 0
            
            if ratio > card_thresh and df[col].dtype == 'object':
                table_report['stats']['statistical_profiling']['high_cardinality_cols'].append(col)
                self._add_violation(table_report, "pilar_3", "WARNING", f"Alta Cardinalidad en '{col}': Ratio {ratio:.2f}")
                stats_issues = True
            if unique_count == 1:
                table_report['stats']['statistical_profiling']['zero_variance_cols'].append(col)
                self._add_violation(table_report, "pilar_3", "WARNING", f"Varianza Cero en '{col}': Columna constante.")
                stats_issues = True
            if pd.api.types.is_numeric_dtype(df[col]):
                z_pct = float((df[col] == 0).mean())
                if z_pct > zero_pct_thresh:
                    table_report['stats']['statistical_profiling']['high_zero_pct_cols'].append(col)
                    self._add_violation(table_report, "pilar_3", "WARNING", f"Inercia de Ceros en '{col}': {z_pct:.1%}")
                    stats_issues = True

        if not stats_issues:
            self._add_passed_check(table_report, "pilar_3", "Estabilidad Estadística: Sin problemas de cardinalidad o varianza.")
        
        # Drift Check
        self._check_drift(table_name, df, table_report)

    def _check_drift(self, table_name, df, table_report):
        table_snapshot = self.snapshot.get('tables', {}).get(table_name, {})
        drift_limit = self.contract.get('monitoring_strategy', {}).get('trend_analysis', {}).get('drift_threshold_pct', 12) / 100
        drift_issues = False
        for col in df.select_dtypes(include=['number']).columns:
            if col in table_snapshot.get('columns', {}):
                snap_mean = table_snapshot['columns'][col].get('mean')
                if snap_mean and snap_mean != 0:
                    drift = abs(float(df[col].mean()) - snap_mean) / snap_mean
                    if drift > drift_limit:
                        self._add_violation(table_report, "pilar_3", "WARNING", f"Data Drift en '{col}': {drift:.1%} (Límite {drift_limit:.0%})")
                        drift_issues = True
        if not drift_issues:
            self._add_passed_check(table_report, "pilar_3", f"Control de Estabilidad (Drift): OK (< {drift_limit:.0%}).")

    def _audit_pilar_4(self, table_name, df, table_report):
        """Domain Logic (Pillar 4)."""
        table_contract = self.contract['tables'][table_name]
        if 'rules' not in table_contract: 
            self._add_passed_check(table_report, "pilar_4", "Sin reglas de dominio para esta tabla.")
            return
        
        for rule_name, rule_body in table_contract['rules'].items():
            rule_str = f"if ({rule_body.get('condition')}) then ({rule_body.get('rule')})" if rule_body.get('condition') else rule_body.get('rule')
            results = self.rules_engine.evaluate_rule(df, rule_str)
            failures = len(results) - results.sum()
            if failures > 0:
                self._add_violation(table_report, "pilar_4", rule_body.get('severity', 'WARNING'), f"Regla '{rule_name}' falló en {failures} registros.")
            else:
                self._add_passed_check(table_report, "pilar_4", f"Regla de Dominio '{rule_name}': OK (100% cumplimiento).")

    def _add_violation(self, table_report, pilar_key, severity, message):
        violation = {"severity": severity, "message": message, "timestamp": datetime.now().isoformat()}
        table_report['pillars'][pilar_key]['violations'].append(violation)
        
        # Also add to the top-level list of the table report for easier access
        table_report['violations'].append(violation)
        
        if severity == "FAILURE":
            table_report['pillars'][pilar_key]['status'] = "FAILURE"
            self.report['summary']['failure_count'] += 1
            self.report['summary']['status'] = "FAILURE"
            self.report['summary']['pillars'][pilar_key]['status'] = "FAILURE"
        else:
            self.report['summary']['warning_count'] += 1
            if self.report['summary']['status'] != "FAILURE": self.report['summary']['status'] = "WARNING"
            if self.report['summary']['pillars'][pilar_key]['status'] != "FAILURE": self.report['summary']['pillars'][pilar_key]['status'] = "WARNING"
            
        self.report['summary']['total_violations'] += 1
        self.report['summary']['pillars'][pilar_key]['violations_count'] += 1

    def _add_passed_check(self, table_report, pilar_key, message):
        check = {"status": "SUCCESS", "message": message}
        if check not in table_report['pillars'][pilar_key]['passed_checks']:
            table_report['pillars'][pilar_key]['passed_checks'].append(check)
            table_report['passed_checks'].append(check)
            self.report['summary']['pillars'][pilar_key]['passed_checks_count'] += 1

    def _consolidate_table_report(self, table_report):
        worst = "SUCCESS"
        for p in table_report['pillars'].values():
            if p['status'] == "FAILURE": worst = "FAILURE"; break
            if p['status'] == "WARNING": worst = "WARNING"
        table_report['status'] = worst

    def calculate_score(self):
        f, w = self.report['summary']['failure_count'], self.report['summary']['warning_count']
        score = max(0, 100 - (f * 10) - (w * 1))
        self.report['summary']['health_score'] = float(score)
        return score

    def save_report(self, path):
        self.calculate_score()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.report, f, indent=4, ensure_ascii=False)
