"""
Main Orchestrator: Forecaster Buñuelitos
Central pipeline entry point following First-Prod methodology.
"""
import argparse
import logging
import sys
import os
from src.utils.config_loader import load_config
from src.loader import DataLoader
from src.preprocessor import Preprocessor

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
        # Phase 01: LOAD
        # Run Phase 01 in 'load' or 'train' modes
        if mode in ["load", "train"]:
            logger.info("--- Starting Phase 01: Data Loading & Validation ---")
            loader = DataLoader(config)
            results = loader.process_all_tables()
            logger.info(f"Phase 01 Completed. Results: {results}")

            # Escalation Rule: If any table failed, stop the entire pipeline
            if any(status == "FAILED" for status in results.values()):
                logger.error("🛑 CRÍTICO: Una o más tablas fallaron la validación en Fase 01. NO CONTINUAR.")
                if mode == "load": sys.exit(1)
                else: 
                     logger.warning("Pipeline continues but subsequent phases might be blocked by handshake.")

        # Phase 02: PREPROCESSING
        # Run Phase 02 in 'train' or 'forecast' modes
        if mode in ["train", "forecast"]:
            logger.info("--- Starting Phase 02: Preprocessing & Data Healing ---")
            prepro = Preprocessor(config)
            status_p2 = prepro.run()
            logger.info(f"Phase 02 Completed with Status: {status_p2}")
            
            if status_p2 == "FAILED":
                logger.error("🛑 CRÍTICO: Fase 02 falló. Abortando pipeline.")
                sys.exit(1)

        # Future Phases...
        if mode == "forecast":
             logger.warning("Phase 03: Forecasting not yet implemented.")

        if mode == "simulate":
             logger.warning("Phase 04: Simulation not yet implemented.")

        logger.info("✅ Pipeline execution finished successfully.")

    except Exception as e:
        logger.error(f"❌ Pipeline Failed: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
