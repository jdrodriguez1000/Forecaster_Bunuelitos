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
