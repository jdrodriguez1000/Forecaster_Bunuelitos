import os
import shutil
import pytest
import pandas as pd
import numpy as np
import json
from unittest.mock import MagicMock, patch
from src.preprocessor import Preprocessor

@pytest.fixture
def functional_config():
    return {
        'general': {
            'project_name': 'Forecaster Buñuelitos Phase 02 Functional',
            'data_raw_path': 'tests/temp/functional/data/01_raw',
            'data_cleansed_path': 'tests/temp/functional/data/02_cleansed',
            'outputs_path': 'tests/temp/functional/outputs',
            'mode': 'train'
        },
        'extractions': {
            'tables': ['ventas', 'finances'],
            'columns': {
                'ventas': ['unidades_totales', 'updated_at', 'valor'],
                'finances': ['price', 'updated_at']
            }
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
                    'reconstruction_steps': [
                        {
                            'step': 1,
                            'name': 'Fill Null Units',
                            'target': 'unidades_totales',
                            'action': 'if_nan_then_logic',
                            'rule': '0'
                        }
                    ]
                },
                'finances': {
                    'reconstruction_steps': []
                }
            }
        }
    }

@pytest.fixture(autouse=True)
def setup_teardown_dirs():
    temp_root = 'tests/temp/functional'
    # More robust cleanup on Windows 
    if os.path.exists(temp_root):
        import time
        for _ in range(3):
            try:
                shutil.rmtree(temp_root, ignore_errors=False)
                break
            except PermissionError:
                time.sleep(0.2)
        else:
            shutil.rmtree(temp_root, ignore_errors=True) # Last resort
            
    os.makedirs(os.path.join(temp_root, 'data/01_raw'), exist_ok=True)
    os.makedirs(os.path.join(temp_root, 'data/02_cleansed'), exist_ok=True)
    os.makedirs(os.path.join(temp_root, 'outputs/reports/phase_02'), exist_ok=True)
    yield
    # No teardown cleanup to avoid locks across test runs

@patch('src.preprocessor.DBConnector')
def test_functional_zero_gaps_law(mock_db, functional_config):
    """
    Scenario: Data has a 1-day gap.
    Expectation: Preprocessor must fill the gap and apply smart filling (ffill).
    """
    raw_path = functional_config['general']['data_raw_path']
    
    # Ventas: 2024-01-01 and 2024-01-03 (Gap on 01-02)
    df_ventas = pd.DataFrame({
        'fecha': pd.to_datetime(['2024-01-01', '2024-01-03']),
        'unidades_totales': [10.0, 30.0],
        'valor': [100, 300],
        'updated_at': pd.Timestamp('2024-01-04')
    })
    df_ventas.to_parquet(os.path.join(raw_path, 'ventas.parquet'))
    
    # Finances: 2024-01-01 and 2024-01-03
    df_finances = pd.DataFrame({
        'fecha': pd.to_datetime(['2024-01-01', '2024-01-03']),
        'price': [20.0, 22.0],
        'updated_at': pd.Timestamp('2024-01-04')
    })
    df_finances.to_parquet(os.path.join(raw_path, 'finances.parquet'))
    
    # Mock Handshake
    client = mock_db.return_value.get_client.return_value
    
    def handshake_side_effect(table_name):
        mock = MagicMock()
        if table_name == 'data_inventory_status':
            mock.select.return_value.in_.return_value.execute.return_value.data = [
                {'table_name': 'ventas', 'status': 'SUCCESS', 'health_score': 100, 'last_data_date': '2024-01-02'},
                {'table_name': 'finances', 'status': 'SUCCESS', 'health_score': 100, 'last_data_date': '2024-01-02'}
            ]
        elif table_name == 'pipeline_execution_status':
            mock.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                {'phase': 'LOAD', 'status': 'SUCCESS'}
            ]
        return mock
    
    client.table.side_effect = handshake_side_effect
    
    preprocessor = Preprocessor(functional_config)
    with patch('src.preprocessor.datetime') as mock_dt:
        mock_dt.now.return_value.date.return_value = pd.Timestamp('2024-01-10').date()
        preprocessor.run()
    
    # Verify Continuity
    master_df = pd.read_parquet(os.path.join(functional_config['general']['data_cleansed_path'], 'master_cleansed.parquet'))
    
    assert len(master_df) == 3 # 01, 02, 03
    assert pd.Timestamp('2024-01-02') in master_df['fecha'].values
    
    # Check smart filling
    row_gap = master_df[master_df['fecha'] == '2024-01-02'].iloc[0]
    assert not np.isnan(row_gap['price']) # ffill worked
    assert row_gap['unidades_totales'] == 0 # our rule for ventas: if_nan_then_logic '0'

@patch('src.preprocessor.DBConnector')
def test_functional_quality_gate_failure_on_duplicates(mock_db, functional_config):
    """
    Scenario: Data has duplicate dates for the same domain.
    Expectation: Quality gate must fail the phase.
    """
    raw_path = functional_config['general']['data_raw_path']
    
    # Ventas with duplicate date
    df_ventas = pd.DataFrame([
        {'fecha': '2024-01-01', 'unidades_totales': 10, 'updated_at': '2024-01-01 10:00:00', 'valor': 100, 'categoria': 'A'},
        {'fecha': '2024-01-01', 'unidades_totales': 20, 'updated_at': '2024-01-01 11:00:00', 'valor': 200, 'categoria': 'A'},
    ])
    # We bypass _load_raw_domain deduplication by creating a file that ALREADY has them 
    # but with same updated_at so it doesn't deduplicate or we carefully craft it.
    # Actually _load_raw_domain deduplicates. To fail quality gate, we need duplicates AFTER merging or persistent ones.
    # The Quality Gate checks for duplicates in the FINAL master.
    
    df_ventas.to_parquet(os.path.join(raw_path, 'ventas.parquet'))
    
    client = mock_db.return_value.get_client.return_value
    
    def handshake_failure_side_effect(table_name):
        mock = MagicMock()
        if table_name == 'data_inventory_status':
            mock.select.return_value.in_.return_value.execute.return_value.data = [
                {'table_name': 'ventas', 'status': 'SUCCESS', 'health_score': 100, 'last_data_date': '2024-01-02'}
            ]
        elif table_name == 'pipeline_execution_status':
            mock.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                {'phase': 'LOAD', 'status': 'SUCCESS'}
            ]
        return mock
    
    client.table.side_effect = handshake_failure_side_effect
    
    # Force Preprocessor to NOT deduplicate by setting strategy to something that won't help
    functional_config['preprocessing']['global_settings']['deduplication_strategy']['order'] = 'none' # Hypothetical
    
    preprocessor = Preprocessor(functional_config)
    
    # We manually patch _load_raw_domain to return duplicates 
    # AND patch _consolidate_master to NOT deduplicate, so we can test the Quality Gate
    with patch.object(Preprocessor, '_load_raw_domain', return_value=df_ventas), \
         patch.object(Preprocessor, '_consolidate_master', return_value=df_ventas), \
         patch('src.preprocessor.datetime') as mock_dt:
        
        mock_dt.now.return_value.date.return_value = pd.Timestamp('2024-01-10').date()
        status = preprocessor.run()
        
    assert status == "FAILED"
    
    report_file = os.path.join(functional_config['general']['outputs_path'], 'reports/phase_02/phase_02_preprocessing_latest.json')
    with open(report_file, 'r') as f:
        report = json.load(f)
    assert report['execution_summary']['overall_status'] == 'FAILED'
    assert 'Duplicate dates detected' in report['execution_summary']['summary']
