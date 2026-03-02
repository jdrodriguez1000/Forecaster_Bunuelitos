import pytest
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from src.utils.data_health_auditor import DataHealthAuditor

@pytest.fixture
def auditor():
    return DataHealthAuditor("tests/fixtures/dummy_contract.yaml", "tests/fixtures/dummy_snapshot.json")

def test_pilar_1_structural_integrity(auditor, sample_df):
    # Happy path
    report = auditor.audit_dataframe('ventas', sample_df)
    assert report['pillars']['pilar_1']['status'] == "SUCCESS"
    assert "Tipos de datos certificados" in str(report['pillars']['pilar_1']['passed_checks'])

def test_pilar_1_missing_columns(auditor):
    df = pd.DataFrame({'fecha': [date.today()]}) # Missing many columns
    report = auditor.audit_dataframe('ventas', df)
    assert report['pillars']['pilar_1']['status'] == "FAILURE"
    assert any("Columnas ausentes" in v['message'] for v in report['pillars']['pilar_1']['violations'])

def test_pilar_2_frontera_temporal(auditor):
    # Today - 1 -> Gap 1 -> SUCCESS (Al día)
    df = pd.DataFrame({'fecha': [date.today() - timedelta(days=1)]})
    report = auditor.audit_dataframe('ventas', df)
    assert any("Frontera Temporal: Al día" in c['message'] for c in report['pillars']['pilar_2']['passed_checks'])

    # Today -> Gap 0 -> WARNING (Sobrecarga / Leakage)
    df_today = pd.DataFrame({'fecha': [date.today()]})
    report_today = auditor.audit_dataframe('ventas', df_today)
    assert any("Sobrecarga de datos" in v['message'] for v in report_today['pillars']['pilar_2']['violations'])

    # Old date -> Gap > 1 -> FAILURE (Brecha)
    old_date = date.today() - timedelta(days=5)
    df_old = pd.DataFrame({'fecha': [old_date]})
    report_old = auditor.audit_dataframe('ventas', df_old)
    assert any("Brecha de 5 días detectada" in v['message'] for v in report_old['pillars']['pilar_2']['violations'])

def test_pilar_2_masse_consistency(auditor):
    # Snapshot has 3346 rows for ~3346 days (1 reg/day)
    # If we provide 10 rows for 10 days -> OK
    dates = pd.date_range(end=date.today(), periods=10, freq='D')
    # Provide all columns to avoid Pillar 1 failures and Rule Evaluation errors
    df = pd.DataFrame({
        'fecha': dates, 
        'unidades_totales': [100]*10,
        'unidades_pagas': [100]*10,
        'unidades_bonificadas': [0]*10,
        'es_promocion': [0]*10,
        'categoria': ['A']*10
    })
    report = auditor.audit_dataframe('ventas', df)
    # Pillar 1 should be SUCCESS now
    assert report['pillars']['pilar_1']['status'] == "SUCCESS"
    
    passed_messages = [c['message'] for c in report['pillars']['pilar_2']['passed_checks']]
    found = any("Consistencia de Masa" in msg for msg in passed_messages)
    assert found, f"Message 'Consistencia de Masa' not found in: {passed_messages}"

    # If we provide 2 rows for 10 days -> FAILURE (Sub-reporte)
    # len=2, days=10 -> 0.2 reg/day. Historical is 1.0.
    df_sparse = pd.DataFrame({
        'fecha': [date.today() - timedelta(days=9), date.today()],
        'unidades_totales': [100, 100],
        'unidades_pagas': [100, 100],
        'unidades_bonificadas': [0, 0],
        'es_promocion': [0, 0],
        'categoria': ['A', 'A']
    })
    report_sparse = auditor.audit_dataframe('ventas', df_sparse)
    
    assert any("Inconsistencia de Sincronización" in v['message'] for v in report_sparse['pillars']['pilar_2']['violations'])

def test_pilar_3_statistical_drift(auditor):
    # Snapshot mean for price in finances is 100.0. Limit 12%.
    # Current mean 150.0 -> Drift 50% -> WARNING
    df = pd.DataFrame({'fecha': [date.today()], 'price': [150.0]})
    report = auditor.audit_dataframe('finances', df)
    assert any("Data Drift en 'price'" in v['message'] for v in report['pillars']['pilar_3']['violations'])

def test_pilar_4_domain_rules(auditor, sample_df):
    # logic_sum: unidades_totales == unidades_pagas + unidades_bonificadas
    # sample_df has 100 == 100 + 0 (PASS)
    report = auditor.audit_dataframe('ventas', sample_df)
    assert any("logic_sum': OK" in c['message'] for c in report['pillars']['pilar_4']['passed_checks'])

    # Induce failure
    df_fail = sample_df.copy()
    df_fail.loc[0, 'unidades_totales'] = 999 
    report_fail = auditor.audit_dataframe('ventas', df_fail)
    assert any("Regla 'logic_sum' falló" in v['message'] for v in report_fail['pillars']['pilar_4']['violations'])

def test_integrity_metrics_stats(auditor, df_with_duplicates):
    # DF with 1 duplicate row and 2 duplicate dates
    report = auditor.audit_dataframe('ventas', df_with_duplicates)
    assert report['stats']['integrity_metrics']['duplicate_rows'] == 1
    assert report['stats']['integrity_metrics']['duplicate_dates'] == 2

def test_sentinel_hits(auditor, df_with_sentinels):
    report = auditor.audit_dataframe('ventas', df_with_sentinels)
    # df_with_sentinels has 3 hits: -999, NULL, 1900-01-01
    assert report['stats']['integrity_metrics']['sentinel_hits'] == 3
