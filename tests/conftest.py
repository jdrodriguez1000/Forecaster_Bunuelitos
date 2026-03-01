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
        'es_promocion': [0, 0, 1, 1, 0, 0, 1, 1, 0, 0]
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
