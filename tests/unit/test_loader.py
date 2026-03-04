import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from src.loader import DataLoader

@pytest.fixture
def mock_config():
    return {
        'supabase': {
            'url': 'https://example.supabase.co',
            'key': 'dummy_key'
        },
        'extractions': {
            'tables': ['ventas', 'clima']
        },
        'general': {
            'data_raw_path': 'data/01_raw',
            'reports_path': 'outputs/reports/phase_01'
        },
        'paths': {
            'contract': 'tests/fixtures/dummy_contract.yaml',
            'snapshot': 'tests/fixtures/dummy_snapshot.json'
        },
        'project': {
            'name': 'Forecaster Buñuelitos TEST'
        }
    }

@patch('src.loader.DBConnector')
@patch('src.loader.DataHealthAuditor')
@patch('src.loader.DataLoader._handshake')
def test_loader_initialization(mock_handshake, mock_auditor_class, mock_db_class, mock_config):
    # Test that the loader initializes correctly with config
    mock_db = mock_db_class.return_value
    mock_db.get_client.return_value = MagicMock()
    
    mock_handshake.return_value = {
        'ruta_contrato_yaml': 'tests/fixtures/dummy_contract.yaml',
        'ruta_snapshot_json': 'tests/fixtures/dummy_snapshot.json',
        'contract_id': 'v1_test',
        'contract_db_id': 1
    }
    
    loader = DataLoader(mock_config)
    assert loader.config == mock_config
    assert mock_db.get_client.called
    assert mock_auditor_class.called

@patch('src.loader.DBConnector')
@patch('src.loader.DataHealthAuditor')
@patch('src.loader.DataLoader._handshake')
def test_loader_run_audit_only(mock_handshake, mock_auditor_class, mock_db_class, mock_config):
    # Mocking DB and Auditor
    mock_db = mock_db_class.return_value
    mock_db.get_client.return_value = MagicMock()
    
    mock_handshake.return_value = {
        'ruta_contrato_yaml': 'tests/fixtures/dummy_contract.yaml',
        'ruta_snapshot_json': 'tests/fixtures/dummy_snapshot.json',
        'contract_id': 'v1_test',
        'contract_db_id': 1
    }
    
    mock_auditor = mock_auditor_class.return_value
    mock_auditor.audit_dataframe.return_value = {'status': 'SUCCESS', 'violations': [], 'stats': {}}
    
    loader = DataLoader(mock_config)
    
    # Mock local data existence
    with patch('os.path.exists', return_value=True), \
         patch('pandas.read_parquet', return_value=pd.DataFrame({'fecha': ['2024-01-01']})), \
         patch('src.loader.DataLoader._save_phase_report') as mock_save, \
         patch('src.loader.DataLoader._get_incremental_info', return_value={'last_data_date': '1900-01-01'}):
        
        # DataLoader has process_all_tables
        loader.process_all_tables() 
        
        assert mock_save.called

@patch('src.loader.DBConnector')
@patch('src.loader.DataHealthAuditor')
@patch('src.loader.DataLoader._handshake')
def test_get_incremental_info_no_data(mock_handshake, mock_auditor_class, mock_db_class, mock_config):
    # Mock DB and client
    mock_db = mock_db_class.return_value
    mock_client = MagicMock()
    mock_db.get_client.return_value = mock_client
    
    mock_handshake.return_value = {
        'ruta_contrato_yaml': 'tests/fixtures/dummy_contract.yaml',
        'ruta_snapshot_json': 'tests/fixtures/dummy_snapshot.json',
        'contract_id': 'v1_test',
        'contract_db_id': 1
    }
    
    # Mock result to return empty data for _get_incremental_info (SELECT)
    mock_select_response = MagicMock()
    mock_select_response.data = []
    
    # Mock result for the INSERT that follows (res_ins)
    mock_insert_response = MagicMock()
    mock_insert_response.data = [{'last_data_date': '1900-01-01', 'table_name': 'ventas'}]
    
    # Mock client call chain
    mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_select_response
    mock_client.table.return_value.insert.return_value.execute.return_value = mock_insert_response
    
    loader = DataLoader(mock_config)
    info = loader._get_incremental_info('ventas')
    
    # Should find the 1900-01-01 in the newly inserted data
    assert info['last_data_date'] == '1900-01-01'

def test_apply_type_conversion(mock_config):
    # Setup dummy config with date_columns (DataLoader uses date_columns, NOT datetime_columns)
    mock_config['extractions']['date_columns'] = ['fecha', 'otro_campo']
    
    with patch('src.loader.DBConnector'), \
         patch('src.loader.DataHealthAuditor'), \
         patch('src.loader.DataLoader._handshake'):
        
        loader = DataLoader(mock_config)
        # Mock the contract in the auditor
        loader.auditor.contract = {
            'tables': {
                'ventas': {
                    'columns': {
                        'fecha': {'type': 'datetime'},
                        'otro_campo': {'type': 'datetime'},
                        'valor': {'type': 'int'}
                    }
                }
            }
        }

        df = pd.DataFrame({
            'fecha': ['2024-01-01', '2024-01-02'],
            'otro_campo': ['2024-01-03', 'invalid'],
            'valor': [100.0, 200.0]
        })
        
        # Now requires table_name
        df_converted = loader._apply_type_conversion(df, 'ventas')
        
        assert pd.api.types.is_datetime64_any_dtype(df_converted['fecha'])
        assert pd.api.types.is_datetime64_any_dtype(df_converted['otro_campo'])
        assert pd.isna(df_converted['otro_campo'].iloc[1])
        # valor 100.0 became float, should be int after conversion
        assert pd.api.types.is_integer_dtype(df_converted['valor'])

@patch('src.loader.DBConnector')
@patch('src.loader.DataHealthAuditor')
@patch('src.loader.DataLoader._handshake')
def test_audit_copy_isolation(mock_handshake, mock_auditor_class, mock_db_class, mock_config):
    # This test ensures that the auditor doesn't modify the source dataframe 
    # despite creating temp columns during its rules evaluation.
    mock_db = mock_db_class.return_value
    mock_db.get_client.return_value = MagicMock()
    
    mock_handshake.return_value = {
        'ruta_contrato_yaml': 'tests/fixtures/dummy_contract.yaml',
        'ruta_snapshot_json': 'tests/fixtures/dummy_snapshot.json',
        'contract_id': 'v1_test',
        'contract_db_id': 1
    }
    
    # Simulate an auditor that adds a technical column
    def audit_with_leak(table, df):
        df['__temp_leak'] = True
        return {'status': 'SUCCESS', 'violations': [], 'stats': {}}
    
    mock_auditor = mock_auditor_class.return_value
    mock_auditor.audit_dataframe.side_effect = audit_with_leak
    
    loader = DataLoader(mock_config)
    
    # Mock download to return valid data and ensure no local file interference
    with patch('os.path.exists', return_value=False), \
         patch('src.loader.DataLoader._download_delta', return_value=pd.DataFrame({'fecha': ['2024-01-01']})) as mock_dl, \
         patch('src.loader.DataLoader._save_phase_report'), \
         patch('src.loader.DataLoader._get_incremental_info', return_value={'last_data_date': '1900-01-01'}), \
         patch('pandas.DataFrame.to_parquet') as mock_to_parquet:
        
        loader.process_all_tables()
        
        # Test isolation: The original dataframe returned by _download_delta 
        # should remain untouched because the auditor received a .copy()
        original_df = mock_dl.return_value
        assert '__temp_leak' not in original_df.columns
