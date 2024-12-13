# Standard Library Imports
from typing import Optional

# Third-Party Imports
from langchain_huggingface import HuggingFaceEmbeddings

# Local Imports
from server.core.config import get_settings
from server.core.logging import setup_logger

class EmbeddingService:
    """Service for managing embeddings operations"""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = setup_logger(__name__)
        self.embeddings = EmbeddingService._initialize_embeddings(self.settings, self.logger)

    @staticmethod
    #@st.cache_resource
    def _initialize_embeddings(_settings, _logger) -> HuggingFaceEmbeddings:
        """Initialize and cache the HuggingFace embeddings model.
        
        Args:
            _settings: Application settings (not hashed by Streamlit)
            _logger: Logger instance (not hashed by Streamlit)
            
        Returns:
            HuggingFaceEmbeddings: Cached embeddings model instance
        """
        _logger.info("Embeddings initialization started...")
        try:
            embeddings = HuggingFaceEmbeddings(
                model_name=_settings.EMBEDDING_MODEL,
                model_kwargs={'device': 'cpu', "trust_remote_code": True},
                encode_kwargs={'normalize_embeddings': False}
            )
            _logger.info("Embeddings initialized successfully.")
            return embeddings
        except Exception as e:
            _logger.error(f"Failed to initialize embeddings: {e}")
            raise

    def get_embeddings(self) -> Optional[HuggingFaceEmbeddings]:
        """Get the cached embeddings model."""
        return self.embeddings 