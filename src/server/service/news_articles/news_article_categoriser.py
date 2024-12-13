# Python Imports
import json
import os
import random
import time
from enum import Enum
from functools import wraps

# Third Party Imports
from langchain_core.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError
from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError, CursorNotFound

# Local Imports
from server.core.config import logger, MongoDBConnections
from server.service.llm_service import OpenAI

logger.info("Starting news article categorization process")

class ErrorCategory(Enum):
    """Enum for categorizing different types of errors."""
    TRANSIENT = 1
    RATE_LIMIT = 2
    PERMANENT = 3

def categorize_error(exception):
    """Categorize the given exception into one of the ErrorCategory types."""
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
    """Decorator that implements an advanced retry mechanism with exponential backoff."""
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

                    factor = rate_limit_factor if error_category == ErrorCategory.RATE_LIMIT else transient_factor
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

def find_data_dir():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    data_dir = os.path.join(parent_dir, 'data')
    return data_dir

def load_research_topics():
    data_dir = find_data_dir()
    file_path = os.path.join(data_dir, 'topics_singleword_keywords.json')
    
    logger.info(f"Loading research topics from {file_path}")
    
    with open(file_path, 'r') as file:
        data = json.load(file)
    
    research_topics = {}
    for item in data:
        topic = item.get('research_topic')
        definition = item.get('definition', '')
        
        if isinstance(topic, list):
            # Combine nested arrays
            combined_topic = ' & '.join(word.split()[-1] for word in topic)
            combined_topic = f"{topic[0].split()[0]} {combined_topic}"
            research_topics[combined_topic] = definition
            logger.info(f"Combined topic: {combined_topic}")
        elif isinstance(topic, str):
            research_topics[topic] = definition
            logger.info(f"Added topic: {topic}")
    
    logger.info(f"Loaded {len(research_topics)} research topics")
    return research_topics

# Load the research topics
research_topics = load_research_topics()
logger.info(f"Loaded {len(research_topics)} research topics")

# Create a string of categories with their definitions for the prompt
categories = "; ".join([f"{topic}: {definition}" for topic, definition in research_topics.items()])
logger.info(f"Categories with definitions prepared for prompt")

# Define the Pydantic model for the output
class CategoryOutput(BaseModel):
    category: str = Field(description="The category of the article")

    @field_validator('category')
    def category_must_be_valid(cls, v: str) -> str:
        if v not in research_topics:
            raise PydanticCustomError(
                'invalid_category',
                'Category must be one of the valid research topics. Got {category}',
                {'category': v}
            )
        return v

# Create the Pydantic output parser
parser = PydanticOutputParser(pydantic_object=CategoryOutput)
format_instructions = parser.get_format_instructions()

# Modify the prompt to include format instructions
prompt = ChatPromptTemplate.from_template(
    """
    <background_information>
    You are an expert at categorizing article text into predefined categories.
    You will be given articles summaries primarily focused on topics related to gender within the Caribbean.
    </background_information>
    
    <objective>
    Given the summary below, categorize it into one of these categories. Each category is followed by its definition which should be used to guide your categorization:
    {categories}
    </objective>
    
    <article_summary>
    {summary}
    </article_summary>
    
    <constraints>
    Tone: Professional
    Style: Gender Expert
    Audience: Journalists, Researchers, Lecturers, Gender Activists
    Response Format: {format_instructions}
    ONLY use the categories provided
    ONLY output a single category
    </constraints>
    
    <article_category>
    [insert category here]
    </article_category>
    """
)

# Create the LCEL chain using OpenAI model
openai = OpenAI()
model = openai.get_model("gpt4o")
chain = prompt | model | parser
logger.info("Created LCEL chain with OpenAI GPT-4 model")

@advanced_retry_with_exponential_backoff(
    max_retries=10,
    base_delay=7,
    transient_factor=1.5,
    rate_limit_factor=2,
    exceptions_to_check=(Exception,)
)
def categorize_article(article, chain, categories, format_instructions):
    if 'msbm_llm_summary' in article:
        summary = article['msbm_llm_summary']
        category = chain.invoke({
            "categories": categories,
            "summary": summary,
            "format_instructions": format_instructions
        })
        logger.info(f"Categorized article: {article['title']} as {category.category}")
        return article['_id'], category.category
    else:
        logger.warning(f"Article missing summary: {article.get('title', 'Unknown title')}")
        return None, None

def perform_bulk_update(collection, bulk_updates):
    if not bulk_updates:
        return
    logger.info(f"Performing bulk update for {len(bulk_updates)} documents")
    try:
        result = collection.bulk_write([UpdateOne({'_id': update[0]}, {'$set': {'msbm_category': update[1]}}) for update in bulk_updates])
        logger.info(f"Bulk updated {result.modified_count} documents")
    except BulkWriteError as bwe:
        logger.error(f"Bulk write error: {bwe.details}")

def categorize_articles():
    logger.info("Starting article categorization")
    try:
        client = MongoClient(MongoDBConnections.MONGODB_CONNECTION_STRING)
        db = client[MongoDBConnections.MONGODB_DB_NAME]
        collection = db['articles']

        cursor = collection.find({
            "$or": [
                {"msbm_category": {"$exists": False}},
                {"msbm_category": ""}
            ]
        }).batch_size(100).max_time_ms(1800000)  # 30 minutes timeout

        total_count = collection.count_documents({
            "$or": [
                {"msbm_category": {"$exists": False}},
                {"msbm_category": ""}
            ]
        })
        logger.info(f"Found {total_count} articles to categorize")

        categorized_count = 0
        error_count = 0
        bulk_updates = []

        while True:
            try:
                for article in cursor:
                    try:
                        article_id, category = categorize_article(article, chain, categories, format_instructions)
                        if article_id and category:
                            bulk_updates.append((article_id, category))
                            categorized_count += 1

                            if len(bulk_updates) >= 50:
                                perform_bulk_update(collection, bulk_updates)
                                bulk_updates = []
                                logger.info(f"Categorized {categorized_count} out of {total_count} articles")
                    except Exception as exc:
                        error_count += 1
                        logger.warning(f'Article generated an exception: {exc}')

                break  # Exit the while loop if we've processed all documents without a CursorNotFound error
            except CursorNotFound:
                last_id = article['_id'] if 'article' in locals() else None
                if last_id:
                    cursor = collection.find({
                        "$or": [
                            {"msbm_category": {"$exists": False}},
                            {"msbm_category": ""}
                        ],
                        "_id": {"$gt": last_id}
                    }).batch_size(100).max_time_ms(1800000)
                    logger.info(f"Cursor timed out. Resuming from article {last_id}")
                else:
                    logger.warning("Cursor timed out and unable to resume. Exiting.")
                    break

        if bulk_updates:
            perform_bulk_update(collection, bulk_updates)

        logger.info(f"Categorization complete. Successful: {categorized_count}, Errors: {error_count}")

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
    finally:
        client.close()
        logger.info("Article categorization completed")

if __name__ == "__main__":
    categorize_articles()