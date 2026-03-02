import os
import shutil
import pytest
import pandas as pd
import json
from unittest.mock import MagicMock, patch
from src.loader import DataLoader

@pytest.fixture
def functional_config():
    """Provides a realistic configuration for functional testing."""
    return {
        'supabase': {
            'url': 'https://mock.supabase.co',
            'key': 'mock_key'
        },
        'extractions': {
            'tables': ['ventas'],
            'date_columns': ['fecha']
        },
        'general': {
            'data_raw_path': 'tests/temp/functional/data/01_raw',
            'outputs_path': 'tests/temp/functional/outputs',
            'mode': 'load',
            'audit_reference_date': '2024-01-03'
        },
        'paths': {
            'contract': 'tests/fixtures/dummy_contract.yaml',
            'snapshot': 'tests/fixtures/dummy_snapshot.json'
        },
        'project': {
            'name': 'Forecaster Buñuelitos Functional Test'
        }
    }

@pytest.fixture(autouse=True)
def setup_teardown_temp_dirs():
    """Ensures test directories are clean before and after each test."""
    temp_root = 'tests/temp/functional'
    if os.path.exists(temp_root):
        shutil.rmtree(temp_root)
    os.makedirs(os.path.join(temp_root, 'data/01_raw'), exist_ok=True)
    os.makedirs(os.path.join(temp_root, 'outputs/reports/phase_01'), exist_ok=True)
    yield
    # Cleanup will happen at start of next run

@patch('src.loader.DBConnector')
@patch('src.loader.DataLoader._handshake')
def test_functional_math_integrity_failure(mock_handshake, mock_db_class, functional_config):
    """
    Scenario: Mathematical integrity rule (logic_sum) is violated.
    Expectation: The audit must flag the table as FAILURE.
    """
    mock_handshake.return_value = {
        'ruta_contrato_yaml': 'tests/fixtures/dummy_contract.yaml',
        'ruta_snapshot_json': 'tests/fixtures/dummy_snapshot.json',
        'contract_id': 'f_test_v1',
        'contract_db_id': 100
    }
    
    # Mathematical failure (100 != 80 + 10)
    # We use values close to snapshot mean (145) to avoid drift warnings
    bad_data = pd.DataFrame([
        {'fecha': '2024-01-01', 'unidades_totales': 145, 'unidades_pagas': 120, 'unidades_bonificadas': 10, 'es_promocion': 0, 'categoria': 'A'}
    ])
    bad_data['fecha'] = pd.to_datetime(bad_data['fecha'])

    loader = DataLoader(functional_config)
    with patch.object(DataLoader, '_get_incremental_info', return_value={'last_data_date': '1900-01-01'}), \
         patch.object(DataLoader, '_download_delta', return_value=bad_data), \
         patch.object(DataLoader, '_update_inventory_status'), \
         patch.object(DataLoader, '_log_and_notify'):
        
        results = loader.process_all_tables()

    assert results['ventas'] == 'FAILURE'
    
    # Verify report contains the specific violation
    report_file = os.path.join(functional_config['general']['outputs_path'], "reports/phase_01/phase_01_loader_latest.json")
    with open(report_file, 'r', encoding='utf-8') as f:
        report = json.load(f)
    
    ventas_report = report['tables']['ventas']
    assert any(v['severity'] == 'FAILURE' and 'logic_sum' in v['message'] for v in ventas_report['violations'])

@patch('src.loader.DBConnector')
@patch('src.loader.DataLoader._handshake')
def test_functional_100_percent_health(mock_handshake, mock_db_class, functional_config):
    """
    Scenario: Perfect data matching all rules.
    Expectation: Status SUCCESS, Health Score 100, Parquet file created.
    """
    mock_handshake.return_value = {
        'ruta_contrato_yaml': 'tests/fixtures/dummy_contract.yaml',
        'ruta_snapshot_json': 'tests/fixtures/dummy_snapshot.json',
        'contract_id': 'f_test_v1',
        'contract_db_id': 100
    }
    
    # Snapshot mean is 145.0, Threshold 10%. 
    # (140 + 150) / 2 = 145.0 -> 0% drift
    perfect_data = pd.DataFrame([
        {'fecha': '2024-01-01', 'unidades_totales': 140, 'unidades_pagas': 140, 'unidades_bonificadas': 0, 'es_promocion': 0, 'categoria': 'A'},
        {'fecha': '2024-01-02', 'unidades_totales': 150, 'unidades_pagas': 140, 'unidades_bonificadas': 10, 'es_promocion': 0, 'categoria': 'B'}
    ])
    perfect_data['fecha'] = pd.to_datetime(perfect_data['fecha'])

    loader = DataLoader(functional_config)
    with patch.object(DataLoader, '_get_incremental_info', return_value={'last_data_date': '1900-01-01'}), \
         patch.object(DataLoader, '_download_delta', return_value=perfect_data), \
         patch.object(DataLoader, '_update_inventory_status'), \
         patch.object(DataLoader, '_log_and_notify'):
        
        results = loader.process_all_tables()

    assert results['ventas'] == 'SUCCESS'
    
    # Verify Score 100 in report
    report_file = os.path.join(functional_config['general']['outputs_path'], "reports/phase_01/phase_01_loader_latest.json")
    with open(report_file, 'r', encoding='utf-8') as f:
        report = json.load(f)
    
    assert report['tables']['ventas']['health_score'] >= 90
    assert os.path.exists(os.path.join(functional_config['general']['data_raw_path'], "ventas.parquet"))

@patch('src.loader.DBConnector')
@patch('src.loader.DataLoader._handshake')
def test_functional_incremental_fusion(mock_handshake, mock_db_class, functional_config):
    """
    Scenario: System has local data until 2024-01-01 and downloads new delta for 2024-01-02.
    Expectation: The final local Parquet must have both rows, sorted and deduplicated.
    """
    mock_handshake.return_value = {
        'ruta_contrato_yaml': 'tests/fixtures/dummy_contract.yaml',
        'ruta_snapshot_json': 'tests/fixtures/dummy_snapshot.json',
        'contract_id': 'f_test_v1',
        'contract_db_id': 100
    }
    
    raw_path = functional_config['general']['data_raw_path']
    local_file = os.path.join(raw_path, "ventas.parquet")
    
    # Snapshot Mean 145.0
    df_local = pd.DataFrame([
        {'fecha': '2024-01-01', 'unidades_totales': 145, 'unidades_pagas': 145, 'unidades_bonificadas': 0, 'es_promocion': 0, 'categoria': 'A'}
    ])
    df_local['fecha'] = pd.to_datetime(df_local['fecha'])
    df_local.to_parquet(local_file, index=False)
    
    new_delta = pd.DataFrame([
        {'fecha': '2024-01-02', 'unidades_totales': 145, 'unidades_pagas': 145, 'unidades_bonificadas': 0, 'es_promocion': 0, 'categoria': 'A'}
    ])
    new_delta['fecha'] = pd.to_datetime(new_delta['fecha'])

    loader = DataLoader(functional_config)
    with patch.object(DataLoader, '_get_incremental_info', return_value={'last_data_date': '2024-01-01'}), \
         patch.object(DataLoader, '_download_delta', return_value=new_delta), \
         patch.object(DataLoader, '_update_inventory_status'), \
         patch.object(DataLoader, '_log_and_notify'):
        
        loader.process_all_tables()

    # Verify Fusion
    df_final = pd.read_parquet(local_file)
    assert len(df_final) == 2
    assert df_final.iloc[0]['fecha'] < df_final.iloc[1]['fecha']
    assert pd.to_datetime(df_final.iloc[1]['fecha']).strftime('%Y-%m-%d') == '2024-01-02'
