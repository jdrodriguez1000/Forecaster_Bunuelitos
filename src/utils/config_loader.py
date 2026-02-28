"""
Config Loader Module
Loads and parses the config.yaml file.
"""
import yaml

def load_config(config_path="config.yaml"):
    with open(config_path, "r") as f:
        return yaml.safe_load(f)
