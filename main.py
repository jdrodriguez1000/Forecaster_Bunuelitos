"""
Main Orchestrator: Forecaster Buñuelitos
Central pipeline entry point following First-Prod methodology.
"""
import argparse
import logging
import sys
from src.utils.config_loader import load_config
from src.loader import DataLoader

def setup_logging():
    """Configure structured logging for the pipeline."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('pipeline_execution.log')
        ]
    )

def main():
    setup_logging()
    logger = logging.getLogger("Orchestrator")
    
    parser = argparse.ArgumentParser(description="Forecaster Buñuelitos Pipeline")
    parser.add_argument("--mode", choices=["load", "train", "forecast", "simulate"], help="Override config mode")
    args = parser.parse_args()
    
    config = load_config()
    # Priority: CLI argument > config.yaml value
    mode = args.mode if args.mode else config['general']['mode']
    
    logger.info(f"🚀 Initializing Forecaster Buñuelitos Pipeline in [{mode.upper()}] mode")

    try:
        if mode == "load":
            logger.info("Starting Phase 01: Data Loading & Validation...")
            loader = DataLoader(config)
            results = loader.process_all_tables()
            logger.info(f"Phase 01 Completed. Results: {results}")

            # Escalation Rule: If any table failed, stop the entire pipeline
            if any(status == "FAILURE" for status in results.values()):
                logger.error("🛑 CRÍTICO: Una o más tablas fallaron la validación. NO CONTINUAR.")
                sys.exit(1)

        elif mode == "train":
            logger.warning("Phase 02: Training not yet implemented.")
            
        elif mode == "forecast":
            logger.warning("Phase 03: Forecasting not yet implemented.")

        elif mode == "simulate":
            logger.warning("Phase 04: Simulation not yet implemented.")

        logger.info("✅ Pipeline execution finished successfully.")

    except Exception as e:
        logger.error(f"❌ Pipeline Failed: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
