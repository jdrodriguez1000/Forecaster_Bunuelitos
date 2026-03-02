import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.utils.data_health_auditor import DataHealthAuditor

@pytest.fixture
def auditor():
    return DataHealthAuditor("tests/fixtures/dummy_contract.yaml", "tests/fixtures/dummy_snapshot.json")

def test_audit_dataframe_basic(auditor, sample_df):
    # Snapshot mean exists in dummy_snapshot for 'ventas' -> 'unidades_totales' (145.0)
    report = auditor.audit_dataframe('ventas', sample_df)
    
    # Check table structure
    assert 'violations' in report
    assert 'stats' in report
    assert report['stats']['row_count'] == 10
    
    # All rules should pass by default for a happy path
    # Except if the rules are defined correctly
    assert len(report['violations']) == 0

def test_health_score_logic(auditor):
    # Induce failures and warnings manually in a mock report to test scoring math
    # Scoring: 100 - (failures * 10) - (warnings * 1)
    
    # 2 failures, 5 warnings -> 100 - 2*10 - 5*1 = 100 - 20 - 5 = 75
    table_report = {'violations': []}
    auditor._add_violation(table_report, "FAILURE", "Fatal Error 1")
    auditor._add_violation(table_report, "FAILURE", "Fatal Error 2")
    for i in range(5):
        auditor._add_violation(table_report, "WARNING", f"Caution {i}")
    
    auditor.save_report("tmp/dummy_report.json")
    assert auditor.report['summary']['health_score'] == 75.0

def test_drift_detection_logic(auditor):
    # Snapshot Mean is 100.
    # Current Horizon Mean is 150. Drift = (150-100)/100 = 50% > threshold
    today = pd.to_datetime(datetime.now().date())
    df = pd.DataFrame({
        'fecha': [today - pd.Timedelta(days=i) for i in range(9, -1, -1)],
        'price': [100.0] * 5 + [150.0] * 5 
    })
    
    # Audit for 'finances' (check table name in dummy_contract and dummy_snapshot)
    report = auditor.audit_dataframe('finances', df, horizon_days=5)
    
    # Should detect 1 horizon drift (last 5 rows are 150)
    # The Global mean of df is (500+750)/10 = 125. (125-100)/100 = 25% > 0.1 threshold
    # So 1 global drift + 1 horizon drift = 2 warnings.
    violations = [v['message'] for v in report['violations']]
    assert any("Global Trend Drift" in m for m in violations)
    assert any("Horizon Drift" in m for m in violations)

def test_freshness_check(auditor):
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    df = pd.DataFrame({'fecha': [yesterday]})
    
    # Ref date matches df -> 0 days diff -> No violation
    auditor.audit_freshness('test', df, today)
    assert auditor.report['summary']['failure_count'] == 0
    
    # Ref date is far away -> 10 days diff -> violation
    far_future = today + timedelta(days=10)
    auditor.audit_freshness('test', df, far_future)
    assert auditor.report['summary']['failure_count'] == 1

def test_audit_integrity_duplicates(auditor, df_with_duplicates):
    # This DF has 1 duplicate row and 2 duplicate dates (2024-01-01 and 2024-01-02)
    report = auditor.audit_dataframe('ventas', df_with_duplicates)
    
    assert report['stats']['integrity']['duplicate_rows'] == 1
    assert report['stats']['integrity']['duplicate_dates'] == 2
    
    violations = [v['message'] for v in report['violations']]
    assert any("Detected 1 exact duplicate rows" in m for m in violations)
    assert any("Detected 2 duplicate dates" in m for m in violations)

def test_audit_integrity_gaps(auditor, df_with_gaps):
    # This DF has gaps between 01-02 and 01-05 (01-03 and 01-04 missing = 2 missing)
    report = auditor.audit_dataframe('ventas', df_with_gaps)
    
    assert report['stats']['integrity']['temporal_gaps'] == 2
    violations = [v['message'] for v in report['violations']]
    assert any("Data continuity breach: 2 missing days" in m for m in violations)

def test_audit_integrity_sentinels(auditor, df_with_sentinels):
    # This DF has 3 sentinels: 1 date (1900-01-01), 1 numeric (-999), 1 object (NULL)
    # Convert fecha to datetime in test to ensure sentinel check works as intended for datetime
    df = df_with_sentinels.copy()
    df['fecha'] = pd.to_datetime(df['fecha'])
    report = auditor.audit_dataframe('ventas', df)
    
    assert report['stats']['integrity']['sentinel_count'] == 3
    violations = [v['message'] for v in report['violations']]
    assert any("Sentinel value(s) detected in 'fecha'" in m for m in violations)
    assert any("Sentinel value(s) detected in 'unidades_totales'" in m for m in violations)
    assert any("Sentinel value(s) detected in 'categoria'" in m for m in violations)
    
    # Check that it lists what it found
    assert any("Found: ['1900-01-01 00:00:00']" in m for m in violations)
    assert any("Found: ['-999']" in m for m in violations)
    assert any("Found: ['NULL']" in m for m in violations)
