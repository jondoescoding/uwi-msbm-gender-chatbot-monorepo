# Built-in imports
import logging
from typing import Dict

# Store logger instances
_loggers: Dict[str, logging.Logger] = {}

def setup_logger(name: str) -> logging.Logger:
    """
    Configure and return a logger with consistent formatting.
    Ensures only one logger instance exists per name.
    
    Args:
        name (str): Name of the logger, typically __name__ from calling module
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # If logger already exists, return it
    if name in _loggers:
        return _loggers[name]
    
    # Create logger
    logger = logging.getLogger(name)
    
    # Only configure if it hasn't been configured before
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Create handler and set level
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(handler)
        
        # Prevent propagation to root logger to avoid duplicate logs
        logger.propagate = False
    
    # Store logger instance
    _loggers[name] = logger
    
    return logger
