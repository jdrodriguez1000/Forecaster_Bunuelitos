"""
Helpers Module
Provides logging and Dual Persistence utilities.
"""
import os
import json
import shutil
from datetime import datetime

def save_dual_persistence(data, base_path, filename):
    """
    Saves data to both 'latest' and 'history' locations.
    Protocol:
    - Latest: base_path/latest_filename.json
    - History: base_path/history/filename_YYYYMMDD_HHMM.json
    """
    os.makedirs(base_path, exist_ok=True)
    history_path = os.path.join(base_path, "history")
    os.makedirs(history_path, exist_ok=True)

    # Prepare filenames
    latest_name = f"{filename}_latest.json"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    history_name = f"{filename}_{timestamp}.json"

    latest_file = os.path.join(base_path, latest_name)
    history_file = os.path.join(history_path, history_name)

    # Save to both
    with open(latest_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    return latest_file, history_file

def save_dual_persistence_markdown(content, base_path, filename):
    """
    Saves markdown content to both 'latest' and 'history' locations.
    Protocol:
    - Latest: base_path/filename.md
    - History: base_path/history/filename_YYYYMMDD_HHMM.md
    """
    os.makedirs(base_path, exist_ok=True)
    history_path = os.path.join(base_path, "history")
    os.makedirs(history_path, exist_ok=True)

    # Prepare filenames
    latest_name = f"{filename}.md"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    history_name = f"{filename}_{timestamp}.md"

    latest_file = os.path.join(base_path, latest_name)
    history_file = os.path.join(history_path, history_name)

    # Save to both
    with open(latest_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    with open(history_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return latest_file, history_file

def setup_logging():
    # Placeholder for standard logging configuration
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger("ForecasterBunuelitos")

