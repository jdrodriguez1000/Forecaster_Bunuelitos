import os
import shutil
import pytest
import pandas as pd
import json
from unittest.mock import MagicMock, patch
from src.loader import DataLoader
from src.preprocessor import Preprocessor

@pytest.fixture
def integration_config():
    """Provides a realistic configuration for integration testing of the whole pipeline."""
    return {
        'general': {
            'project_name': 'Forecaster Buñuelitos Full Integration',
            'data_raw_path': 'tests/temp/integration/data/01_raw',
            'data_cleansed_path': 'tests/temp/integration/data/02_cleansed',
            'outputs_path': 'tests/temp/integration/outputs',
            'mode': 'train',
            'audit_reference_date': '2024-01-03'
        },
        'extractions': {
            'tables': ['ventas', 'finances'],
            'columns': {
                'ventas': ['unidades_totales', 'es_promocion', 'updated_at', 'valor'],
                'finances': ['price', 'updated_at']
            },
            'date_columns': ['fecha']
        },
        'preprocessing': {
            'orchestration': {
                'handshake': {
                    'tables_to_check': ['ventas', 'finances'],
                    'required_status': 'SUCCESS',
                    'min_health_score': 0.8
                },
                'execution_tracking': {
                    'enabled': True,
                    'phase_name': 'PREPROCESSING'
                },
                'incremental': {
                    'mode': 'delta'
                }
            },
            'global_settings': {
                'anti_leakage_t_minus_1': True,
                'deduplication_strategy': {
                    'by_column': 'updated_at',
                    'order': 'descending'
                },
                'alignment': {
                    'drop_extra_columns': True
                },
                'continuity': {
                    'ensure_zero_gaps': True
                }
            },
            'table_rules': {
                'ventas': {
                    'reconstruction_steps': []
                },
                'finances': {
                    'reconstruction_steps': []
                }
            }
        },
        'supabase': {
            'url': 'https://mock.supabase.co',
            'key': 'mock_key'
        },
        'paths': {
            'contract': 'tests/fixtures/dummy_contract.yaml',
            'snapshot': 'tests/fixtures/dummy_snapshot.json'
        }
    }

@pytest.fixture(autouse=True)
def setup_teardown_dirs():
    """Ensures test directories are clean."""
    temp_root = 'tests/temp/integration'
    if os.path.exists(temp_root):
        shutil.rmtree(temp_root)
    
    os.makedirs(os.path.join(temp_root, 'data/01_raw'), exist_ok=True)
    os.makedirs(os.path.join(temp_root, 'data/02_cleansed'), exist_ok=True)
    os.makedirs(os.path.join(temp_root, 'outputs/reports/phase_01'), exist_ok=True)
    os.makedirs(os.path.join(temp_root, 'outputs/reports/phase_02'), exist_ok=True)
    
    yield
    # Cleanup
    if os.path.exists(temp_root):
        shutil.rmtree(temp_root)

@patch('src.loader.DBConnector')
@patch('src.loader.DataLoader._handshake')
@patch('src.preprocessor.DBConnector')
def test_full_pipeline_flow_phase_1_and_2(mock_pre_db, mock_loader_handshake, mock_loader_db, integration_config):
    """
    Integration test: Phase 01 (Loader) -> Phase 02 (Preprocessor).
    1. Phase 01 loads raw data.
    2. Phase 02 processes raw data into master_cleansed.
    """
    # --- PHASE 01 SETUP ---
    mock_loader_handshake.return_value = {
        'ruta_contrato_yaml': 'tests/fixtures/dummy_contract.yaml',
        'ruta_snapshot_json': 'tests/fixtures/dummy_snapshot.json',
        'contract_id': 'int_test',
        'contract_db_id': 1
    }
    
    loader_db = mock_loader_db.return_value
    loader_client = MagicMock()
    loader_db.get_client.return_value = loader_client
    
    # Mock data for Phase 01
    mock_ventas = [
        {'fecha': '2024-01-01', 'unidades_totales': 10, 'unidades_pagas': 10, 'unidades_bonificadas': 0, 'valor': 100, 'es_promocion': 0, 'updated_at': '2024-01-01 10:00:00', 'categoria': 'A'},
        {'fecha': '2024-01-02', 'unidades_totales': 15, 'unidades_pagas': 15, 'unidades_bonificadas': 0, 'valor': 150, 'es_promocion': 0, 'updated_at': '2024-01-02 10:00:00', 'categoria': 'A'}
    ]
    mock_finances = [
        {'fecha': '2024-01-01', 'price': 50.0, 'updated_at': '2024-01-01 10:00:00'},
        {'fecha': '2024-01-02', 'price': 60.0, 'updated_at': '2024-01-02 10:00:00'}
    ]
    
    def side_effect(table_name):
        chain = MagicMock()
        data = mock_ventas if table_name == 'ventas' else mock_finances
        chain.select.return_value.gt.return_value.order.return_value.range.return_value.execute.return_value.data = data
        return chain
    
    loader_client.table.side_effect = side_effect
    
    # Run Phase 01
    loader = DataLoader(integration_config)
    with patch.object(DataLoader, '_get_incremental_info', return_value={'last_data_date': '1900-01-01'}), \
         patch.object(DataLoader, '_update_inventory_status'), \
         patch.object(DataLoader, '_log_and_notify'):
        loader.process_all_tables()
    
    # Verify Phase 01 outputs
    assert os.path.exists(os.path.join(integration_config['general']['data_raw_path'], 'ventas.parquet'))
    assert os.path.exists(os.path.join(integration_config['general']['data_raw_path'], 'finances.parquet'))
    
    # --- PHASE 02 SETUP ---
    pre_db = mock_pre_db.return_value
    pre_client = MagicMock()
    pre_db.get_client.return_value = pre_client
    
    # Mock for Phase 02 handshake reading from Supabase
    # In real scenario, Preprocessor reads from data_inventory_status and pipeline_execution_status
    mock_inventory_status = MagicMock()
    mock_inventory_status.select.return_value.in_.return_value.execute.return_value.data = [
        {'table_name': 'ventas', 'status': 'SUCCESS', 'health_score': 100, 'last_data_date': '2024-01-02'},
        {'table_name': 'finances', 'status': 'SUCCESS', 'health_score': 100, 'last_data_date': '2024-01-02'}
    ]
    
    mock_execution_status = MagicMock()
    mock_execution_status.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {'phase': 'LOAD', 'status': 'SUCCESS'}
    ]
    
    def pre_side_effect(table_name):
        if table_name == 'data_inventory_status': return mock_inventory_status
        if table_name == 'pipeline_execution_status': return mock_execution_status
        return MagicMock()
    
    pre_client.table.side_effect = pre_side_effect
    
    # Run Phase 02
    preprocessor = Preprocessor(integration_config)
    
    # Mocking now() to avoid anti-leakage triggering on our static test data
    with patch('src.preprocessor.datetime') as mock_dt:
        mock_dt.now.return_value.date.return_value = pd.Timestamp('2024-01-10').date()
        status = preprocessor.run()
    
    if status != "SUCCESS":
        report_file = os.path.join(integration_config['general']['outputs_path'], 'reports/phase_02/phase_02_preprocessing_latest.json')
        if os.path.exists(report_file):
            with open(report_file, 'r') as f:
                rep = json.load(f)
                print(f"\nDEBUG: FAILED STATUS SUMMARY: {rep['execution_summary']['summary']}")
    
    assert status == "SUCCESS"
    master_file = os.path.join(integration_config['general']['data_cleansed_path'], 'master_cleansed.parquet')
    assert os.path.exists(master_file)
    
    df_master = pd.read_parquet(master_file)
    print("\nDEBUG: Master DF Columns:", df_master.columns.tolist())
    print("DEBUG: Master DF Nulls:\n", df_master.isnull().sum())
    
    # Master should have columns from both tables joined by fecha
    assert 'unidades_totales' in df_master.columns
    assert 'price' in df_master.columns
    assert len(df_master) == 2
    
    # Check Phase 02 report
    report_file = os.path.join(integration_config['general']['outputs_path'], 'reports/phase_02/phase_02_preprocessing_latest.json')
    assert os.path.exists(report_file)
    with open(report_file, 'r') as f:
        report = json.load(f)
    
    assert report['execution_summary']['overall_status'] == 'SUCCESS'
    assert 'quality_metrics' in report
    assert report['quality_metrics']['total_rows'] == 2
