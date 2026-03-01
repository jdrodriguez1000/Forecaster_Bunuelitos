import pytest
import pandas as pd
import numpy as np
from src.utils.business_rules_engine import BusinessRulesEngine

def test_arithmetic_rule_evaluation():
    engine = BusinessRulesEngine()
    df = pd.DataFrame({
        'a': [1, 2, 3],
        'b': [4, 5, 6],
        'c': [5, 7, 9]
    })
    rule = "c == a + b"
    results = engine.evaluate_rule(df, rule)
    assert results.all() == True

    df.loc[2, 'c'] = 0 # Fail 
    results = engine.evaluate_rule(df, rule)
    assert not results.all()
    assert results.sum() == 2

def test_if_then_conversion():
    engine = BusinessRulesEngine()
    df = pd.DataFrame({
        'es_promocion': [0, 1, 1],
        'unidades_pagas': [100, 100, 0]
    })
    # If it is a promo, unidades_pagas must be > 0
    # Rule: if es_promocion == 1 then unidades_pagas > 0
    rule = "if es_promocion == 1 then unidades_pagas > 0"
    results = engine.evaluate_rule(df, rule)
    
    # Row 0: es_promocion=0, units=100 -> If condition FALSE, passes
    # Row 1: es_promocion=1, units=100 -> If condition TRUE, consequence TRUE, passes
    # Row 2: es_promocion=1, units=0   -> If condition TRUE, consequence FALSE, FAILS
    assert results[0] == True
    assert results[1] == True
    assert results[2] == False

def test_time_lag_minus_n():
    engine = BusinessRulesEngine()
    df = pd.DataFrame({
        'a': [10, 20, 30, 40]
    })
    # Current a == Previous a + 10
    rule = "a == a_t_minus_1 + 10"
    results = engine.evaluate_rule(df, rule)
    
    # Row 0: shift(1) is NaN -> Fillna(True) -> passes
    # Row 1: 20 == 10 + 10 -> TRUE
    # Row 2: 30 == 20 + 10 -> TRUE
    # Row 3: 40 == 30 + 10 -> TRUE
    assert results.all() == True

def test_time_lead_plus_n():
    engine = BusinessRulesEngine()
    df = pd.DataFrame({
        'a': [10, 20, 30, 40]
    })
    # Current a == Next a - 10
    rule = "a == a_t_plus_1 - 10"
    results = engine.evaluate_rule(df, rule)
    
    # Row 0: 10 == 20 - 10 -> TRUE
    # Row 1: 20 == 30 - 10 -> TRUE
    # Row 2: 30 == 40 - 10 -> TRUE
    # Row 3: shift(-1) is NaN -> Fillna(True) -> passes
    assert results.all() == True

def test_cleanup_temps():
    engine = BusinessRulesEngine()
    df = pd.DataFrame({'val': [1, 2]})
    engine.evaluate_rule(df, "val == val_t_minus_1 + 1")
    assert any(c.startswith("__temp_") for c in df.columns)
    
    engine.cleanup_temps(df)
    assert not any(c.startswith("__temp_") for c in df.columns)

def test_rule_error_graceful_failure():
    engine = BusinessRulesEngine()
    df = pd.DataFrame({'a': [1, 2]})
    # Invalid syntax or missing column
    rule = "b + a == 10"
    results = engine.evaluate_rule(df, rule)
    # Should return all False indicators for security (not a pass)
    assert not results.any()
