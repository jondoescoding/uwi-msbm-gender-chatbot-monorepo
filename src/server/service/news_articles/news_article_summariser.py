"""
News Article Summariser

This script processes news articles stored in a MongoDB database, generating summaries using a language model.
It implements an advanced retry mechanism with exponential backoff for error handling and rate limiting.

Key components:
- MongoDB connection and document processing
- Language model integration for text summarization
- Advanced retry mechanism with error categorization
- Bulk update operations for efficient database updates
"""

# Local Imports
from backend.core.config import MongoDBConnections
from backend.core.config import logger
from backend.service.llm_service import OpenAI

# Python Imports
from enum import Enum
from functools import wraps
import random
import time

# Third Party Imports
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_experimental.text_splitter import SemanticChunker
from langchain_huggingface import HuggingFaceEmbeddings
from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError, CursorNotFound

# Setup of the LLM
llm_provider = OpenAI()
llm = llm_provider.get_model("gpt4o")

class ErrorCategory(Enum):
    """Enum for categorizing different types of errors."""
    TRANSIENT = 1
    RATE_LIMIT = 2
    PERMANENT = 3

def categorize_error(exception):
    """
    Categorize the given exception into one of the ErrorCategory types.
    
    Args:
    exception (Exception): The exception to categorize.
    
    Returns:
    ErrorCategory: The category of the error.
    """
    if isinstance(exception, (ConnectionError, TimeoutError)):
        return ErrorCategory.TRANSIENT
    elif isinstance(exception, Exception) and "rate limit" in str(exception).lower():
        return ErrorCategory.RATE_LIMIT
    else:
        return ErrorCategory.PERMANENT

def advanced_retry_with_exponential_backoff(
    max_retries=5,
    base_delay=3,
    max_delay=300,
    transient_factor=1.5,
    rate_limit_factor=2,
    exceptions_to_check=(Exception,)
):
    """
    Decorator that implements an advanced retry mechanism with exponential backoff.
    
    Args:
    max_retries (int): Maximum number of retry attempts.
    base_delay (float): Initial delay between retries in seconds.
    max_delay (float): Maximum delay between retries in seconds.
    transient_factor (float): Multiplier for delay on transient errors.
    rate_limit_factor (float): Multiplier for delay on rate limit errors.
    exceptions_to_check (tuple): Exceptions to catch and retry on.
    
    Returns:
    function: Decorated function with retry logic.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions_to_check as e:
                    retries += 1
                    error_category = categorize_error(e)
                    
                    if error_category == ErrorCategory.PERMANENT:
                        logger.error(f"Permanent error encountered: {str(e)}")
                        raise e

                    if retries == max_retries:
                        logger.error(f"Max retries reached. Last error: {str(e)}")
                        raise e

                    if error_category == ErrorCategory.RATE_LIMIT:
                        factor = rate_limit_factor
                    else:  # TRANSIENT
                        factor = transient_factor

                    delay = min(base_delay * (factor ** retries), max_delay)
                    jitter = random.uniform(0, 1)
                    total_delay = delay + jitter

                    logger.info(f"Retry {retries}/{max_retries}. "
                                f"Error category: {error_category.name}. "
                                f"Sleeping for {total_delay:.2f} seconds")
                    time.sleep(total_delay)
            return func(*args, **kwargs)
        return wrapper
    return decorator

logger.info("Initializing HuggingFace Embeddings")
embeddings = HuggingFaceEmbeddings(
    model_name="Snowflake/snowflake-arctic-embed-s",
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True}
)

logger.info("Creating SemanticChunker")
text_splitter = SemanticChunker(embeddings)

logger.info("Setting up prompts")
summary_prompt = """
<background_information>
You are an expert at summarising article text.
You will be given articles primarily focused on topics related to gender within the Caribbean.
</background_information>

<objective>
Craft a summary that is detailed, thorough, in-depth, and complex, while maintaining clarity and conciseness. 
</objective>

<constraints>
Word Count: 75
Tone: Professional
Style: Gender Expert
Audience: Journalists, Researchers, Lecturers, Gender Activists
Response Format: Paragraph with no other prose than the summary and ONLY rely on the provided text, without including external information.
</constraints>

<article_context>
{context}
</article_context>
"""

stuff_prompt = ChatPromptTemplate.from_messages(
    [("human", summary_prompt)]
)

logger.info("Setting up the stuff documents chain")
stuff_chain = create_stuff_documents_chain(llm=llm, prompt=stuff_prompt)

@advanced_retry_with_exponential_backoff(
    max_retries=10,
    base_delay=7,
    transient_factor=1.5,
    rate_limit_factor=2,
    exceptions_to_check=(Exception,)
)
def process_single_document(document, stuff_chain, collection, bulk_updates):
    """
    Process a single document, generate a summary, and prepare for bulk update.
    
    Args:
    document (dict): The document to process.
    stuff_chain (Chain): The language model chain for summarization.
    collection (Collection): MongoDB collection.
    bulk_updates (list): List to store bulk update operations.
    
    Returns:
    bool: True if document was processed successfully, False otherwise.
    """
    logger.info(f"Processing document {document['_id']}")

    if 'content' not in document or not document['content']:
        logger.warning(f"Document {document['_id']} has no or empty content. Skipping.")
        return False

    content = document['content']
    docs = text_splitter.create_documents([content])

    summary = stuff_chain.invoke({"context": docs})
    logger.info(f"Article processed for document: {document['_id']}")
    
    bulk_updates.append({
        'filter': {'_id': document['_id']},
        'update': {'$set': {'msbm_llm_summary': summary}}
    })
    return True

def perform_bulk_update(collection, bulk_updates):
    """
    Perform bulk update operation on the MongoDB collection.
    
    Args:
    collection (Collection): MongoDB collection to update.
    bulk_updates (list): List of update operations to perform.
    """
    if not bulk_updates:
        return
    logger.info(f"Performing bulk update for {len(bulk_updates)} documents")
    try:
        result = collection.bulk_write([UpdateOne(update['filter'], update['update']) for update in bulk_updates])
        logger.info(f"Bulk updated {result.modified_count} documents")
        bulk_updates.clear()
    except BulkWriteError as bwe:
        logger.error(f"Bulk write error: {bwe.details}")

def process_documents():
    """
    Main function to process documents from MongoDB, generate summaries, and update the database.
    """
    logger.info("Starting document processing")
    try:
        client = MongoClient(MongoDBConnections.MONGODB_CONNECTION_STRING)
        db = client[MongoDBConnections.MONGODB_DB_NAME]
        collection = db['articles']

        # Increase the cursor timeout and use batch processing
        cursor = collection.find({
            "$or": [
                {"msbm_llm_summary": {"$exists": False}},
                {"msbm_llm_summary": ""}
            ]
        }).batch_size(100).max_time_ms(1800000)  # 30 minutes timeout
        
        bulk_updates = []
        processed_count = 0
        skipped_count = 0
        total_count = collection.count_documents({
            "$or": [
                {"msbm_llm_summary": {"$exists": False}},
                {"msbm_llm_summary": ""}
            ]
        })
        logger.info(f"Found {total_count} documents to process")

        while True:
            try:
                for document in cursor:
                    try:
                        if process_single_document(document, stuff_chain, collection, bulk_updates):
                            processed_count += 1
                        else:
                            skipped_count += 1
                        
                        if len(bulk_updates) >= 50:  # Perform bulk update every 50 documents
                            perform_bulk_update(collection, bulk_updates)
                            bulk_updates = []
                            logger.info(f"Processed {processed_count} out of {total_count} documents")
                    except Exception as e:
                        logger.error(f"Error processing document {document['_id']}: {str(e)}")
                        skipped_count += 1

                break  # Exit the while loop if we've processed all documents without a CursorNotFound error
            except CursorNotFound:
                # If cursor times out, create a new one starting from the last processed document
                last_id = document['_id'] if 'document' in locals() else None
                if last_id:
                    cursor = collection.find({
                        "$or": [
                            {"msbm_llm_summary": {"$exists": False}},
                            {"msbm_llm_summary": ""}
                        ],
                        "_id": {"$gt": last_id}
                    }).batch_size(50).max_time_ms(1800000)
                    logger.info(f"Cursor timed out. Resuming from document {last_id}")
                else:
                    logger.warning("Cursor timed out and unable to resume. Exiting.")
                    break

        if bulk_updates:
            perform_bulk_update(collection, bulk_updates)

        logger.info(f"Total documents: {total_count}")
        logger.info(f"Processed documents: {processed_count}")
        logger.info(f"Skipped documents: {skipped_count}")

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
    finally:
        client.close()
        logger.info("Document processing completed")

if __name__ == "__main__":
    process_documents()