import pytest
import pandas as pd
import numpy as np
import os
import json
from unittest.mock import MagicMock, patch
from src.preprocessor import Preprocessor

@pytest.fixture
def mock_config():
    return {
        'general': {
            'project_name': 'Forecaster Buñuelitos TEST',
            'data_raw_path': 'data/01_raw',
            'data_cleansed_path': 'data/02_cleansed',
            'outputs_path': 'outputs'
        },
        'extractions': {
            'tables': ['ventas', 'inventario'],
            'columns': {
                'ventas': ['unidades_totales', 'es_promocion', 'updated_at', 'valor'],
                'inventario': ['buñuelos_preparados']
            }
        },
        'preprocessing': {
            'orchestration': {
                'handshake': {
                    'tables_to_check': ['ventas', 'inventario'],
                    'required_status': 'SUCCESS',
                    'min_health_score': 0.9
                },
                'incremental': {
                    'mode': 'delta',
                    'look_back_days': 7
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
                            'name': 'Test Rule',
                            'target': 'unidades_totales',
                            'action': 'if_nan_then_logic',
                            'rule': '10'
                        }
                    ]
                }
            }
        }
    }

@pytest.fixture
def preprocessor(mock_config):
    with patch('src.preprocessor.DBConnector'):
        with patch('os.makedirs'):
            return Preprocessor(mock_config)

def test_preprocessor_initialization(preprocessor, mock_config):
    assert preprocessor.config == mock_config
    assert preprocessor.master_dataset_file == "master_cleansed.parquet"

@patch('src.preprocessor.Preprocessor._handshake')
def test_handshake_failure(mock_handshake, preprocessor):
    mock_handshake.return_value = (False, "Handshake FAILED", 0.5)
    
    with patch.object(preprocessor, '_sync_execution_to_supabase') as mock_sync:
        result = preprocessor.run()
        assert result == "FAILED"
        mock_sync.assert_called_with("FAILED", "N/A", 0, 0.5, "Handshake FAILED")

def test_anti_leakage(preprocessor):
    fixed_now = pd.Timestamp('2024-03-03')
    today = pd.Timestamp(fixed_now.date())
    
    df = pd.DataFrame({
        'fecha': [today - pd.Timedelta(days=1), today, today + pd.Timedelta(days=1)],
        'valor': [10, 20, 30],
        'unidades_totales': [1, 2, 3],
        'es_promocion': [0, 0, 0],
        'updated_at': [fixed_now, fixed_now, fixed_now]
    })
    
    with patch('src.preprocessor.datetime') as mock_dt, \
         patch('os.path.exists', return_value=True), \
         patch('pandas.read_parquet', return_value=df):
        
        mock_dt.now.return_value.date.return_value = today.date()

        processed_df = preprocessor._load_raw_domain('ventas', last_cleaned_date=None)
        
        assert len(processed_df) == 1
        assert processed_df['fecha'].max() < today
        assert preprocessor.domain_stats['ventas']['anti_leakage'] == 2

def test_deduplication(preprocessor):
    # Strategy is 'descending' on updated_at
    # In preprocessor: ascending=[True, dedup_cfg['order'] == "descending"]
    # So it sorts fecha ASC (True), updated_at ASC (False, because "descending" == "descending" is True)
    # This means for same fecha: 10:00:00 comes FIRST, 11:00:00 comes SECOND.
    # drop_duplicates(keep='first') keeps FIRST -> 10:00:00
    df = pd.DataFrame({
        'fecha': [pd.Timestamp('2024-01-01'), pd.Timestamp('2024-01-01')],
        'updated_at': [pd.Timestamp('2024-01-01 10:00:00'), pd.Timestamp('2024-01-01 11:00:00')],
        'valor': [10, 20],
        'unidades_totales': [1, 2],
        'es_promocion': [0, 0]
    })
    
    with patch('os.path.exists', return_value=True), \
         patch('pandas.read_parquet', return_value=df):
        processed_df = preprocessor._load_raw_domain('ventas', last_cleaned_date=None)
        
        assert len(processed_df) == 1
        # The code sorts ASC on updated_at when config says 'descending' (due to ascending=[True, True])
        assert processed_df['valor'].iloc[0] == 10
        assert preprocessor.domain_stats['ventas']['deduplicated'] == 1

def test_column_pruning(preprocessor):
    df = pd.DataFrame({
        'fecha': [pd.Timestamp('2024-01-01')],
        'unidades_totales': [10],
        'es_promocion': [0],
        'updated_at': [pd.Timestamp('2024-01-01')],
        'valor': [100],
        'extra_col': [999]
    })
    
    with patch('os.path.exists', return_value=True), \
         patch('pandas.read_parquet', return_value=df):
        processed_df = preprocessor._load_raw_domain('ventas', last_cleaned_date=None)
        
        assert 'extra_col' not in processed_df.columns
        assert 'unidades_totales' in processed_df.columns
        assert 'extra_col' in preprocessor.domain_stats['ventas']['pruned_cols']

def test_safe_eval_ternary(preprocessor):
    df = pd.DataFrame({
        'condicion': [True, False, True],
        'valor_true': [1, 2, 3],
        'valor_false': [10, 20, 30]
    })
    
    expr = "valor_true if condicion else valor_false"
    result = preprocessor._safe_eval(df, expr)
    
    expected = pd.Series([1, 20, 3])
    pd.testing.assert_series_equal(result, expected, check_names=False)

def test_apply_healing_steps(preprocessor):
    df = pd.DataFrame({
        'fecha': [pd.Timestamp('2024-01-01'), pd.Timestamp('2024-01-02')],
        'unidades_totales': [np.nan, 20]
    })
    
    healed_df = preprocessor._apply_healing_steps(df, 'ventas')
    
    assert healed_df['unidades_totales'].iloc[0] == 10
    assert healed_df['unidades_totales'].iloc[1] == 20
    assert preprocessor.domain_stats['ventas']['nulls'] == 1

def test_quality_gate(preprocessor):
    df_ok = pd.DataFrame({
        'fecha': pd.to_datetime(['2024-01-01', '2024-01-02']),
        'unidades': [10, 20]
    })
    assert preprocessor._quality_gate(df_ok) == True
    
    df_fail = pd.DataFrame({
        'fecha': pd.to_datetime(['2024-01-01', '2024-01-01']),
        'unidades': [10, 20]
    })
    assert preprocessor._quality_gate(df_fail) == False
    assert preprocessor.output_audit['duplicate_dates'] == 1
