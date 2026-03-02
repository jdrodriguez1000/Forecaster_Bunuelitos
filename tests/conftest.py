import pytest
import pandas as pd
import numpy as np

@pytest.fixture
def sample_df():
    """Provides a standard dataframe for testing business rules and health audit."""
    data = {
        'fecha': pd.date_range(start='2024-01-01', periods=10, freq='D'),
        'unidades_pagas': [100, 110, 120, 130, 140, 150, 160, 170, 180, 190],
        'unidades_bonificadas': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        'unidades_totales': [100, 110, 120, 130, 140, 150, 160, 170, 180, 190],
        'es_promocion': [0, 0, 1, 1, 0, 0, 1, 1, 0, 0],
        'categoria': ['A', 'B', 'A', 'C', 'B', 'A', 'C', 'B', 'A', 'B']
    }
    return pd.DataFrame(data)

@pytest.fixture
def sample_contract():
    """Provides a basic data contract structure."""
    return {
        'ventas': {
            'rules': {
                'logic_sum': {
                    'rule': 'unidades_totales == unidades_pagas + unidades_bonificadas',
                    'severity': 'FAILURE'
                },
                'promo_check': {
                    'condition': 'es_promocion == 1',
                    'rule': 'unidades_pagas > 0',
                    'severity': 'WARNING'
                }
            },
            'columns': {
                'unidades_totales': {'type': 'float', 'drift_threshold': 0.1}
            }
        }
    }
@pytest.fixture
def df_with_duplicates():
    """Provides a dataframe with duplicate rows and duplicate dates."""
    data = {
        'fecha': ['2024-01-01', '2024-01-01', '2024-01-02', '2024-01-02'],
        'unidades_totales': [100, 100, 120, 130] 
    }
    # Row 0 and 1 are identical. Date 2024-01-02 is duplicated but values are different.
    df = pd.DataFrame(data)
    df['fecha'] = pd.to_datetime(df['fecha'])
    return df

@pytest.fixture
def df_with_gaps():
    """Provides a dataframe with missing days in the sequence."""
    data = {
        'fecha': ['2024-01-01', '2024-01-02', '2024-01-05'],
        'unidades_totales': [100, 110, 140]
    }
    df = pd.DataFrame(data)
    df['fecha'] = pd.to_datetime(df['fecha'])
    return df

@pytest.fixture
def df_with_sentinels():
    """Provides a dataframe with sentinel values (dummy markers)."""
    data = {
        'fecha': ['2024-01-01', '1900-01-01', '2024-01-03'],
        'unidades_totales': [100, -999, 120],
        'categoria': ['A', 'NULL', 'B']
    }
    df = pd.DataFrame(data)
    df['fecha'] = pd.to_datetime(df['fecha'])
    return df
