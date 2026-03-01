import pandas as pd
import numpy as np
import re

class BusinessRulesEngine:
    """
    Evaluates complex business rules defined in the Data Contract against a DataFrame.
    Supports row-wise arithmetic, logical comparisons, and time-lagged checks (t_minus_1).
    """

    def evaluate_rule(self, df: pd.DataFrame, rule_str: str) -> pd.Series:
        """
        Evaluates a rule string and returns a boolean Series indicating where the rule is met.
        Returns True for rows that PASS the rule.
        """
        if not rule_str or not isinstance(rule_str, str):
            return pd.Series([True] * len(df)) # Rule is empty, ignore it

        try:
            # Prepare the expression for pandas.eval
            expr = self._preprocess_rule(df, rule_str)
            
            # evaluate returns a boolean series where the condition is TRUE
            result = df.eval(expr)
            
            # Find any temp columns used in this expr to handle edge NaNs (lags/leads)
            # If any temp column involved in the result is NaN, we treat as True (pass)
            temp_cols_used = [c for c in df.columns if c.startswith("__temp_") and c in expr]
            if temp_cols_used:
                # Use a mask where any involved temp column is NaN
                nan_mask = df[temp_cols_used].isna().any(axis=1)
                result[nan_mask] = True
            
            # Handle standard fillna if pandas returns object series with NaNs
            if isinstance(result, pd.Series):
                result = result.fillna(True)
            
            return result
        except Exception as e:
            print(f"Error evaluating rule '{rule_str}': {str(e)}")
            return pd.Series([False] * len(df))

    def _preprocess_rule(self, df: pd.DataFrame, rule_str: str) -> str:
        """
        Converts human-friendly logic (if/then) to boolean expressions
        and handles time-lagged keywords.
        """
        processed_rule = rule_str
        
        # 1. Convert "if A then B" to "(not (A)) | (B)"
        # Note: In boolean logic, (A -> B) is equivalent to (!A v B)
        if "if" in processed_rule.lower() and "then" in processed_rule.lower():
            pattern = re.compile(r"if\s+(.*?)\s+then\s+(.*)", re.IGNORECASE)
            match = pattern.search(processed_rule)
            if match:
                condition = match.group(1).strip()
                consequence = match.group(2).strip()
                processed_rule = f"(~({condition})) | ({consequence})"

        # 2. Detect pattern: column_name_t_minus_N (Time lagged, back)
        matches_minus = re.findall(r'(\w+)_t_minus_(\d+)', processed_rule)
        for col, lag in matches_minus:
            if col in df.columns:
                temp_col_name = f"__temp_{col}_lag{lag}"
                df[temp_col_name] = df[col].shift(int(lag))
                processed_rule = processed_rule.replace(f"{col}_t_minus_{lag}", temp_col_name)

        # 3. Detect pattern: column_name_t_plus_N (Time leading, forward)
        matches_plus = re.findall(r'(\w+)_t_plus_(\d+)', processed_rule)
        for col, lead in matches_plus:
            if col in df.columns:
                temp_col_name = f"__temp_{col}_lead{lead}"
                df[temp_col_name] = df[col].shift(-int(lead))
                processed_rule = processed_rule.replace(f"{col}_t_plus_{lead}", temp_col_name)

        # 4. Handle _t or _T (Current time indicators)
        matches_t = re.findall(r'(\w+)_t\b', processed_rule, re.IGNORECASE)
        for col in matches_t:
            if col in df.columns:
                processed_rule = re.sub(rf'\b{col}_[tT]\b', col, processed_rule)
        
        return processed_rule

    def cleanup_temps(self, df: pd.DataFrame):
        """Removes temporary columns created during preprocessing."""
        temp_cols = [c for c in df.columns if c.startswith("__temp_")]
        df.drop(columns=temp_cols, inplace=True)
