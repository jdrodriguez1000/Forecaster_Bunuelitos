"""
Forecaster Module
Generates 185-day daily forecasts and monthly aggregations.
"""

class Forecaster:
    def __init__(self, config, model):
        self.config = config
        self.model = model

    def predict(self, steps=185):
        pass

    def aggregate_monthly(self, forecast_df):
        pass
