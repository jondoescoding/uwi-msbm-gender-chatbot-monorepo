from langchain_astradb import AstraDBVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from server.core.config import get_settings
from server.core.logging import setup_logger
from typing import Dict, Any

# Setup logger
logger = setup_logger(name=__name__)

class AstraService:
    """Service for AstraDB operations"""
    
    def __init__(self):
        self.settings = get_settings()
        self.embeddings = AstraService._initialize_embeddings(self.settings)
        self.vectorstore = self._initialize_vectorstore(self.settings, self.embeddings)
    
    @staticmethod
    def _initialize_embeddings(_settings) -> HuggingFaceEmbeddings:
        """Initialize HuggingFace embeddings"""
        try:
            return HuggingFaceEmbeddings(
                model_name=_settings.EMBEDDING_MODEL,
                model_kwargs={'device': 'cpu', "trust_remote_code": True},
                encode_kwargs={'normalize_embeddings': False}
            )
        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {e}")
            raise

    @staticmethod
    def _initialize_vectorstore(_settings, _embeddings) -> AstraDBVectorStore:
        """Initialize AstraDB vector store"""
        try:
            return AstraDBVectorStore(
                collection_name=_settings.COLLECTION_NAME,
                embedding=_embeddings,
                api_endpoint=_settings.ASTRA_DB_API_ENDPOINT,
                token=_settings.ASTRA_DB_APPLICATION_TOKEN,
            )
        except Exception as e:
            logger.error(f"Failed to initialize AstraDB: {e}")
            raise

    def search_documents(self, query: str, filters: Dict[str, Any] = None, k: int = 2, fetch_k: int = 20, lambda_mult: float = 0.5):
        """Search documents with MMR"""
        if not (0 <= lambda_mult <= 1):
            logger.warning(f"Invalid lambda_mult value: {lambda_mult}. It must be between 0 and 1.")
            raise ValueError("lambda_mult must be between 0 and 1.")
        
        try:
            retriever = self.vectorstore.as_retriever(
                search_type="mmr",
                search_kwargs={
                    'k': k,
                    'fetch_k': fetch_k,
                    'lambda_mult': lambda_mult,
                    'filter': filters
                }
            )
            return retriever.invoke(query)
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            raise