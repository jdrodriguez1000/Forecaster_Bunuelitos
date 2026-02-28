"""
Main Orchestrator
Central pipeline entry point.
"""
import argparse
from src.utils.config_loader import load_config

def main():
    parser = argparse.ArgumentParser(description="Forecaster Buñuelitos Pipeline")
    parser.add_argument("--mode", choices=["load", "train", "forecast", "simulate"], default="load")
    args = parser.parse_args()
    
    config = load_config()
    print(f"Running pipeline in {args.mode} mode...")

if __name__ == "__main__":
    main()
