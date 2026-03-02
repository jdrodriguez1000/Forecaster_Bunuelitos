import pytest
import pandas as pd
from src.utils.business_rules_engine import BusinessRulesEngine

@pytest.fixture
def engine():
    return BusinessRulesEngine()

def test_basic_arithmetic_rule(engine, sample_df):
    rule = "unidades_totales == unidades_pagas + unidades_bonificadas"
    result = engine.evaluate_rule(sample_df, rule)
    assert result.all() # All rows match in sample_df

def test_if_then_logic(engine, sample_df):
    # if es_promocion == 1 then unidades_pagas > 0
    rule = "if es_promocion == 1 then unidades_pagas > 0"
    result = engine.evaluate_rule(sample_df, rule)
    assert result.all()

def test_day_keyword_logic(engine):
    # Rule using 'day' keyword (automatically extracted from fecha)
    df = pd.DataFrame({
        'fecha': ['2024-01-15', '2024-01-20'],
        'val': [1, 2]
    })
    # if day == 15 then val == 1
    rule = "if day == 15 then val == 1"
    result = engine.evaluate_rule(df, rule)
    assert result.all()

def test_time_lag_logic(engine):
    df = pd.DataFrame({
        'fecha': pd.date_range('2024-01-01', periods=3),
        'ventas': [100, 110, 120]
    })
    # Rule: current sales must be greater than previous day sales
    rule = "ventas > ventas_t_minus_1"
    result = engine.evaluate_rule(df, rule)
    
    # First row is NaN (shifted), so it should return True by engine logic
    assert result[0] == True
    assert result[1] == True # 110 > 100
    assert result[2] == True # 120 > 110

def test_cleanup_temps(engine, sample_df):
    # Use a rule that creates a temp column
    rule = "day == 1"
    engine.evaluate_rule(sample_df, rule)
    assert any(c.startswith("__temp_") for c in sample_df.columns)
    
    engine.cleanup_temps(sample_df)
    assert not any(c.startswith("__temp_") for c in sample_df.columns)
