# Python Imports
import json
import os
from typing import Any, Dict, List

# Third Party Imports
from newscatcherapi_client import ApiException, Newscatcher
import pymongo
from pymongo import MongoClient
from pymongo.errors import BulkWriteError, ConnectionFailure

# Local Imports
from server.core.config import get_settings
from server.core.logging import setup_logger

logger = setup_logger(name=__name__)

LANGUAGES = "AF,AR,BG,BN,CA,CS,CY,CN,DA,DE,EL,EN,ES,ET,FA,FI,FR,GU,HE,HI,HR,HU,ID,IT,JA,KN,KO,LT,LV,MK,ML,MR,NE,NL,NO,PA,PL,PT,RO,RU,SK,SL,SO,SQ,SV,SW,TA,TE,TH,TL,TR,TW,UK,UR,VI"

COUNTRIES = "AI, AG, AW, BS, BB, BZ, BM, BQ, VG, KY, CU, CW, DM, DO, GD, GP, HT, JM, MQ, MS, PR, BL, KN, LC, MF, VC, SX, TT, TC, VI"

settings = get_settings()
NEWS_API_KEY = settings.NEWS_API_KEY
MONGODB_CONNECTION_STRING = settings.MONGODB_CONNECTION_STRING
MONGODB_DB_NAME = settings.MONGODB_DB_NAME

def load_research_topics() -> List[str]:
    """
    Load research topics from the topics.json file.

    Returns:
        List[str]: A list of research topics.

    Raises:
        FileNotFoundError: If the topics.json file is not found.
        json.JSONDecodeError: If there's an error decoding the JSON file.
    """
    try:
        # Update the file path
        data_dir = find_data_dir()
        json_file_path = os.path.join(data_dir, '..', 'data', 'topics_singleword_keywords.json')
        
        logger.info(f"Attempting to load JSON file from: {json_file_path}")
        
        with open(json_file_path, 'r') as file:
            topics_data = json.load(file)
        
        # Extract and flatten the research topics
        topics = []
        for item in topics_data:
            if 'research_topic' in item:
                if isinstance(item['research_topic'], list):
                    topics.extend(item['research_topic'])
                else:
                    topics.append(item['research_topic'])
            else:
                logger.info("Missing 'research_topic' in an item of topics.json")
        
        logger.info(f"Loaded {len(topics)} research topics")
        return topics
    except FileNotFoundError:
        logger.error(f"topics.json file not found at {json_file_path}")
        raise
    except json.JSONDecodeError:
        logger.error(f"Error decoding topics.json at {json_file_path}")
        raise

def fetch_newscatcher_articles(
    api_key: str,
    query: str,
    days_ago: int = 365,
    page_size: int = 1000
) -> List[Dict[Any, Any]]:
    """
    Generic function to fetch news articles using the Newscatcher API.

    Args:
        api_key (str): Newscatcher API key.
        query (str): The search query.
        days_ago (int): Number of days in the past to search for articles. Defaults to 365.
        page_size (int): Number of articles to retrieve per page. Defaults to 1000.

    Returns:
        List[Dict[Any, Any]]: A list of dictionaries, where each dictionary represents an article.

    Raises:
        ValueError: If no API key is provided.
        ApiException: If there's an error in making the API request.
    """
    logger.info(f"Starting to fetch news articles for query: {query}")

    if not api_key:
        logger.error("No API key provided")
        raise ValueError("API key is required.")

    newscatcher = Newscatcher(api_key=api_key)
    logger.debug("Newscatcher API client initialized")

    # Define search parameters
    languages = LANGUAGES
    search_in = 'content, summary, title'
    countries = COUNTRIES

    articles_list = []
    page = 1
    while True:
            try:
                logger.info(f"Fetching page {page} of news articles for query: {query}")
                get_news = newscatcher.search.get(
                    q=query,
                    lang=languages,
                    search_in=search_in,
                    countries=countries,
                    sort_by='date',
                    page_size=page_size,
                    page=page,
                    from_=f'{days_ago} days ago',
                    published_date_precision='full',
                    is_paid_content=False
                )

                articles_list.extend(get_news.articles)
                logger.info(f"Added {len(get_news.articles)} articles from page {page}")

                if page >= get_news.total_pages:
                    logger.info(f"Reached the last page of results for query: {query}")
                    break
                
                page += 1
            except ApiException as e:
                logger.error(f"Exception on page {page} for query '{query}': {e}")
                break
    logger.info(f"Finished fetching news articles. Total articles retrieved: {len(articles_list)}")
    return articles_list

def get_gender_news_articles(
    api_key: str,
    days_ago: int = 365,
    page_size: int = 1000
) -> List[Dict[Any, Any]]:
    """
    Fetches news articles related to gender topics using the Newscatcher API.

    Args:
        api_key (str): Newscatcher API key.
        days_ago (int): Number of days in the past to search for articles. Defaults to 365.
        page_size (int): Number of articles to retrieve per page. Defaults to 1000.

    Returns:
        List[Dict[Any, Any]]: A list of dictionaries, where each dictionary represents an article.

    Raises:
        ValueError: If no API key is provided.
        ApiException: If there's an error in making the API request.
    """
    logger.info(f"Starting to fetch gender news articles for the past {days_ago} days")

    # Load research topics
    topics = load_research_topics()

    gender_news_articles_list = []

    for topic in topics:
        try:
            articles = fetch_newscatcher_articles(api_key, topic, days_ago, page_size)
            gender_news_articles_list.extend(articles)
        except Exception as e:
            logger.error(f"Error fetching articles for topic '{topic}': {e}")

    logger.info(f"Finished fetching gender news articles. Total articles retrieved: {len(gender_news_articles_list)}")
    return gender_news_articles_list

def find_data_dir():
    """Find the data directory of the project."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    while True:
        data_dir = os.path.join(current_dir, 'data')
        if os.path.exists(data_dir):
            return data_dir
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            raise FileNotFoundError("Could not find data directory")
        current_dir = parent_dir

def load_keywords() -> List[str]:
    """
    Load keywords from the topics_singleword_keywords.json file.

    Returns:
        List[str]: A list of unique keywords from all languages.

    Raises:
        FileNotFoundError: If the topics_singleword_keywords.json file is not found.
        json.JSONDecodeError: If there's an error decoding the JSON file.
    """
    try:
        # Find the data directory
        data_dir = find_data_dir()
        
        # Construct the path to the JSON file
        json_file_path = os.path.join(data_dir, 'topics_singleword_keywords.json')
        
        logger.info(f"Attempting to load JSON file from: {json_file_path}")
        
        with open(json_file_path, 'r') as file:
            keywords_data = json.load(file)
        
        # Extract and flatten the keywords from all languages
        keywords = []
        for item in keywords_data:
            if 'keywords' in item:
                for language_keywords in item['keywords'].values():
                    keywords.extend(language_keywords)
        
        # Remove duplicates and sort
        keywords = sorted(set(keywords))
        
        logger.info(f"Loaded {len(keywords)} unique keywords")
        return keywords
    except FileNotFoundError:
        logger.error(f"topics_singleword_keywords.json file not found at {json_file_path}")
        raise
    except json.JSONDecodeError:
        logger.error(f"Error decoding topics_singleword_keywords.json at {json_file_path}")
        raise

def search_newscatcher_by_keywords(
    api_key: str,
    days_ago: int = 365,
    page_size: int = 1000
) -> List[Dict[Any, Any]]:
    """
    Searches for news articles using all keywords across all languages using the Newscatcher API.

    Args:
        api_key (str): Newscatcher API key.
        days_ago (int): Number of days in the past to search for articles. Defaults to 365.
        page_size (int): Number of articles to retrieve per page. Defaults to 1000.

    Returns:
        List[Dict[Any, Any]]: A list of dictionaries, where each dictionary represents an article.

    Raises:
        ValueError: If no API key is provided.
        ApiException: If there's an error in making the API request.
    """
    logger.info(f"Starting to search news articles by keywords for the past {days_ago} days")

    # Load keywords
    keywords = load_keywords()

    news_articles_list = []

    for keyword in keywords:
        try:
            articles = fetch_newscatcher_articles(api_key, keyword, days_ago, page_size)
            news_articles_list.extend(articles)
        except ApiException as e:
            logger.error(f"Error fetching articles for keyword '{keyword}': {e}")

    logger.info(f"Finished fetching news articles by keywords. Total articles retrieved: {len(news_articles_list)}")
    return news_articles_list

def upload_articles_to_mongodb(collection, articles: List[Dict]) -> None:
    """
    Uploads articles to MongoDB using bulk operations, checking for pre-existing articles.

    Args:
        collection: MongoDB collection object.
        articles (List[Dict]): List of articles to upload.
    """
    if not articles:
        logger.info("No articles to upload.")
        return

    # Use bulk write operations for better performance
    bulk_operations = [
        pymongo.UpdateOne({'link': article['link']}, {'$setOnInsert': article}, upsert=True)
        for article in articles
    ]

    try:
        result = collection.bulk_write(bulk_operations)
        logger.info(f"Bulk upserted {result.upserted_count} articles, "
                    f"modified {result.modified_count} articles")
    except BulkWriteError as e:
        logger.error(f"Bulk write error: {str(e)}")

def connect_to_mongodb():
    """
    Establishes a connection to MongoDB and returns the client and collection objects.

    Returns:
        tuple: A tuple containing the MongoDB client and collection objects.

    Raises:
        ConnectionFailure: If unable to connect to MongoDB.
    """
    try:
        client = MongoClient(MONGODB_CONNECTION_STRING)
        client.admin.command('ping')
        logger.info("Successfully connected to MongoDB")

        db = client[MONGODB_DB_NAME]
        collection = db['articles']

        if "link" not in collection.index_information():
            collection.create_index([("link", 1)], unique=True)
            logger.info("Created index on 'link' field")

        return client, collection
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}", exc_info=True)
        raise

def main():
    """
    Main function providing a simple terminal interface for the news collector.
    
    This function handles user input, fetches gender-related news articles,
    searches for articles by keywords, and uploads them to MongoDB. It also 
    provides error handling and proper resource management.
    """
    client = None
    try:
        client, collection = connect_to_mongodb()
        if not NEWS_API_KEY:
            raise ValueError("NEWS_API_KEY is not set in the environment variables.")
        while True:
            logger.info("\nNews Collector Menu:")
            logger.info("1. Fetch and upload categories")
            logger.info("2. Search and upload by keywords")
            logger.info("3. Exit")
            
            choice = input("Enter your choice (1-3): ")
            
            if choice == '1':
                logger.info("Fetching and uploading news...")
                try:
                    articles = get_gender_news_articles(api_key=NEWS_API_KEY)
                    upload_articles_to_mongodb(collection, articles)
                    logger.info(f"Operation completed. Processed {len(articles)} articles.")
                except (ApiException, ValueError) as e:
                    logger.error(f"Error fetching or uploading articles: {str(e)}")
            elif choice == '2':
                logger.info("Searching and uploading news by keywords...")
                try:
                    articles = search_newscatcher_by_keywords(api_key=NEWS_API_KEY)
                    upload_articles_to_mongodb(collection, articles)
                    logger.info(f"Operation completed. Processed {len(articles)} articles.")
                except (ApiException, ValueError) as e:
                    logger.error(f"Error searching or uploading articles: {str(e)}")
            elif choice == '3':
                logger.info("Exiting the program.")
                break
            else:
                logger.warning("Invalid choice. Please try again.")

    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}", exc_info=True)
    finally:
        if client:
            client.close()

if __name__ == "__main__":
    main()
