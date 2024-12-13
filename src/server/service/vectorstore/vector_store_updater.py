# Built-in imports
import uuid

# External library imports
from langchain_core.documents import Document
from langchain_astradb import AstraDBVectorStore
from langchain_mongodb import MongoDBAtlasVectorSearch
from pymongo import MongoClient
from langchain.embeddings import HuggingFaceEmbeddings

# Local application imports
from core.config import get_settings
from core.logging import setup_logger

# Initialize settings and logger
settings = get_settings()
logger = setup_logger(__name__)

def get_embeddings():
    """Initialize and return the embedding model"""
    try:
        return HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)
    except Exception as e:
        logger.error(f"Failed to initialize embeddings: {str(e)}")
        raise

class DatabaseConnectionInit:
    """Class to handle database operations for both AstraDB and MongoDB"""
    
    def __init__(self):
        """Initialize connections to both vector stores"""
        self.embeddings = get_embeddings()
        self._init_astra_db()
        self._init_mongodb()
        
    def _init_astra_db(self):
        """Initialize AstraDB vector store connection"""
        try:
            self.astra_vector_store = AstraDBVectorStore(
                embedding=self.embeddings,
                collection_name=settings.COLLECTION_NAME,
                api_endpoint=settings.ASTRA_DB_API_ENDPOINT,
                token=settings.ASTRA_DB_APPLICATION_TOKEN,
                namespace=settings.ASTRA_DB_NAMESPACE
            )
            logger.info("Connected to AstraDB vector store")
        except Exception as e:
            logger.error(f"Failed to connect to AstraDB: {str(e)}")
            raise
            
    def _init_mongodb(self):
        """Initialize MongoDB connection"""
        try:
            # Connect to MongoDB
            self.mongo_client = MongoClient(settings.MONGODB_CONNECTION_STRING)
            self.mongo_db = self.mongo_client[settings.MONGODB_DB_NAME]
            self.mongo_collection = self.mongo_db['articles']
            
            # Initialize vector store
            self.mongo_vector_store = MongoDBAtlasVectorSearch(
                collection=self.mongo_collection,
                embedding=self.embeddings,
                relevance_score_fn="cosine"
            )
            logger.info("Connected to MongoDB vector store")
        except Exception as e:
            logger.info(f"Failed to connect to MongoDB: {str(e)}")
            raise
            
    def close_connections(self):
        """Close MongoDB client connection"""
        try:
            self.mongo_client.close()
            logger.info("Closed MongoDB connection")
        except Exception as e:
            logger.info(f"Error closing MongoDB connection: {str(e)}")

def get_msbm_articles(database_connection, batch_size=100):
    """
    Query MongoDB for all MSBM Caribbean articles using pagination with PyMongo's native find()
    
    Args:
        database_connection: Instance of DatabaseConnectionInit
        batch_size (int): Number of documents to retrieve per batch
        
    Returns:
        list: All matching MSBM Caribbean articles
    """
    try:
        all_results = []
        
        # Use PyMongo's find() instead of vector search
        cursor = database_connection.mongo_collection.find(
            {"msbm_caribbean_article": {"$eq": "True"}},
            batch_size=batch_size
        )
        
        # Iterate through cursor to get all documents
        for doc in cursor:
            # Convert to Document format for consistency
            document = Document(
                page_content=doc.get('msbm_llm_summary', ''),
                metadata={k:v for k,v in doc.items() if k != 'msbm_llm_summary'}
            )
            all_results.append(document)
            
            if len(all_results) % batch_size == 0:
                logger.info(f"Retrieved {len(all_results)} MSBM articles from MongoDB")
        
        logger.info(f"Retrieved total of {len(all_results)} MSBM articles from MongoDB")
        return all_results
        
    except Exception as e:
        logger.info(f"Failed to query MSBM articles: {str(e)}")
        raise

def add_articles_to_astra(database_connection, articles):
    """
    Add MongoDB articles to AstraDB vector store
    
    Args:
        database_connection: Instance of DatabaseConnectionInit
        articles (list): List of langchain Document objects containing news articles
        
    Returns:
        list: List of inserted document IDs
    """
    try:
        # Create Document objects for vector store
        documents = []
        
        # Fields to exclude from metadata
        exclude_fields = {
            'msbm_llm_summary', 'content', '_id', 'all_domain_links', 
            'all_links', 'country', 'id', 'is_headline', 'is_opinion', 
            'media', 'paid_content', 'published_date_precision', 'rank', 
            'score', 'embedding', 'updated_date_precision', 
            'twitter_account', 'updated_date'
        }
        
        logger.info(f"Processing {len(articles)} articles for AstraDB insertion")
        
        for i, article in enumerate(articles, 1):
            # The content is already in page_content from get_msbm_articles()
            page_content = article.page_content
            
            # Create metadata dict excluding specified fields
            metadata = {k: v for k, v in article.metadata.items() if k not in exclude_fields}
            
            # Create Document object
            doc = Document(
                page_content=page_content,
                metadata=metadata
            )
            documents.append(doc)
            
            if i % 100 == 0:
                logger.info(f"Processed {i}/{len(articles)} articles")
        
        # Generate UUIDs for each document
        logger.info("Generating UUIDs for documents")
        uuids = [str(uuid.uuid4()) for _ in range(len(documents))]
        
        # Add documents to AstraDB vector store
        logger.info("Starting batch insert to AstraDB")
        database_connection.astra_vector_store.add_documents(
            documents=documents,
            ids=uuids
        )
        
        logger.info(f"Successfully added {len(documents)} articles to AstraDB vector store")
        return uuids
        
    except Exception as e:
        logger.info(f"Failed to add articles to AstraDB: {str(e)}")
        raise

def main():
    """
    Main function to handle vector store operations using match-case
    """
    try:
        # Initialize database connections
        database_connection = DatabaseConnectionInit()
        
        while True:
            print("\nVector Store Operations:")
            print("1. Add MSBM Articles to AstraDB")
            print("2. Exit")
            
            choice = input("\nEnter your choice (1-2): ")
            
            match choice:
                case "1":
                    try:
                        # Get MSBM articles from MongoDB
                        articles = get_msbm_articles(database_connection)
                        if not articles:
                            logger.warning("No MSBM articles found in MongoDB")
                            continue
                            
                        # Add articles to AstraDB
                        uuids = add_articles_to_astra(database_connection, articles)
                        logger.info(f"Successfully added {len(uuids)} articles to AstraDB")
                        
                    except Exception as e:
                        logger.info(f"Error processing articles: {str(e)}")
                        
                case "2":
                    logger.info("Exiting application")
                    break
                    
                case _:
                    logger.warning("Invalid choice. Please select 1 or 2")
                    
    except Exception as e:
        logger.info(f"Application error: {str(e)}")
        
    finally:
        # Close database connections
        if 'database_connection' in locals():
            database_connection.close_connections()

if __name__ == "__main__":
    main()
