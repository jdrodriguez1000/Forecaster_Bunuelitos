import os
import shutil
import pytest
import pandas as pd
import json
from unittest.mock import MagicMock, patch
from src.loader import DataLoader

@pytest.fixture
def integration_config():
    """Provides a realistic configuration for integration testing."""
    return {
        'supabase': {
            'url': 'https://mock.supabase.co',
            'key': 'mock_key'
        },
        'extractions': {
            'tables': ['ventas', 'finances'],
            'date_columns': ['fecha', 'updated_at']
        },
        'general': {
            'data_raw_path': 'tests/temp/data/01_raw',
            'outputs_path': 'tests/temp/outputs',
            'mode': 'load',
            'audit_reference_date': '2024-01-03'
        },
        'paths': {
            'contract': 'tests/fixtures/dummy_contract.yaml',
            'snapshot': 'tests/fixtures/dummy_snapshot.json'
        },
        'project': {
            'name': 'Forecaster Buñuelitos Integration Test'
        }
    }

@pytest.fixture(autouse=True)
def setup_teardown_temp_dirs():
    """Ensures test directories are clean before and after each test."""
    temp_dirs = ['tests/temp/data/01_raw', 'tests/temp/outputs/reports/phase_01']
    for d in temp_dirs:
        if os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d, exist_ok=True)
    yield

@patch('src.loader.DBConnector')
@patch('src.loader.DataLoader._handshake')
def test_full_loader_integration_flow(mock_handshake, mock_db_class, integration_config):
    """
    Integration test for Phase 01: Loader & Auditor.
    Mocks the DB extraction but validates the full logic:
    1. Incremental check.
    2. Data download (mocked chain).
    3. File saving (Parquet).
    4. Health Audit execution.
    5. Phase report generation (JSON).
    """
    # 1. Setup Mock DB Response for _handshake
    mock_handshake.return_value = {
        'ruta_contrato_yaml': 'tests/fixtures/dummy_contract.yaml',
        'ruta_snapshot_json': 'tests/fixtures/dummy_snapshot.json',
        'contract_id': 'v1_integration_test',
        'contract_db_id': 99
    }
    
    # 2. Setup Mock Supabase Client and Responses
    mock_db = mock_db_class.return_value
    mock_client = MagicMock()
    mock_db.get_client.return_value = mock_client
    
    mock_data_ventas = [
        {
            'fecha': '2024-01-01', 
            'unidades_totales': 100, 
            'unidades_pagas': 100, 
            'unidades_bonificadas': 0, 
            'es_promocion': 0, 
            'categoria': 'A',
            'updated_at': '2024-01-01 12:00:00',
            'valor': 10000.0
        },
        {
            'fecha': '2024-01-02', 
            'unidades_totales': 120, 
            'unidades_pagas': 120, 
            'unidades_bonificadas': 0, 
            'es_promocion': 0, 
            'categoria': 'B',
            'updated_at': '2024-01-02 12:00:00',
            'valor': 12000.0
        }
    ]
    mock_data_finances = [
        {'fecha': '2024-01-01', 'price': 100.0, 'updated_at': '2024-01-01 12:00:00'},
        {'fecha': '2024-01-02', 'price': 105.0, 'updated_at': '2024-01-02 12:00:00'}
    ]
    
    def table_mock_side_effect(table_name):
        mock_chain = MagicMock()
        data = mock_data_ventas if table_name == 'ventas' else mock_data_finances
        mock_chain.select.return_value.gt.return_value.order.return_value.range.return_value.execute.return_value.data = data
        return mock_chain

    mock_client.table.side_effect = table_mock_side_effect

    # 3. Create Loader and run
    loader = DataLoader(integration_config)
    
    with patch.object(DataLoader, '_get_incremental_info', return_value={'last_data_date': '1900-01-01'}), \
         patch.object(DataLoader, '_update_inventory_status') as mock_update, \
         patch.object(DataLoader, '_log_and_notify') as mock_log_notify:
        
        loader.process_all_tables()

    # 4. Assertions (verify existence before teardown purges them)
    raw_path = integration_config['general']['data_raw_path']
    report_path = os.path.join(integration_config['general']['outputs_path'], "reports", "phase_01")

    assert os.path.exists(os.path.join(raw_path, 'ventas.parquet'))
    assert os.path.exists(os.path.join(raw_path, 'finances.parquet'))
    assert os.path.exists(os.path.join(report_path, 'phase_01_loader_latest.json'))

    with open(os.path.join(report_path, 'phase_01_loader_latest.json'), 'r') as f:
        report = json.load(f)
        
    assert report['metadata']['phase'] == '01'
    assert 'ventas' in report['tables']
    assert report['tables']['ventas']['stats']['row_count'] == 2
