"""
Search Service Module
-------------------
This module handles all database search operations for the news article application.
It provides functionality to connect to MongoDB and retrieve unique country data.

Functions:
    - get_mongodb_connection(): Establishes and returns a MongoDB connection
    - get_unique_countries(): Retrieves unique country names from the database
    - search_articles(): Search articles with filters for category, country, and date range
    - get_saved_dashboards(): Retrieves saved dashboards from MongoDB
    - save_dashboard(): Save a new dashboard to MongoDB
    - update_dashboard_name(): Update a dashboard's name in MongoDB
"""

import pymongo
from pymongo.server_api import ServerApi
from server.core.logging import setup_logger
from src.server.core.config import get_settings
from datetime import datetime
from typing import List, Optional, Dict, Any

# Configure logging - use consistent name without 'src.' prefix
logger = setup_logger("server.service.search_service")

# Get settings once at module level
settings = get_settings()

def get_mongodb_connection():
    """
    Establishes a connection to MongoDB using configuration settings.
    
    Returns:
        pymongo.database.Database: MongoDB database instance
        
    Raises:
        pymongo.errors.ConnectionError: If connection to MongoDB fails
    """
    try:
        logger.info("Attempting to establish MongoDB connection")
        logger.info(f"Using connection string: {settings.MONGODB_CONNECTION_STRING[:10]}...")  # Log only first 10 chars for security
        
        client = pymongo.MongoClient(
            settings.MONGODB_CONNECTION_STRING, 
            server_api=ServerApi('1')
        )
        
        # Verify connection
        client.admin.command('ping')
        logger.info("Successfully connected to MongoDB")
        
        db = client[settings.MONGODB_DB_NAME]
        logger.info(f"Connected to database: {settings.MONGODB_DB_NAME}")
        return db
        
    except Exception as e:
        logger.warning(f"Failed to connect to MongoDB: {str(e)}")
        raise

def get_unique_countries():
    """
    Retrieves a list of unique country names from the database.
    Uses PyMongo's distinct() method for efficient querying.
    
    Returns:
        list: Sorted list of unique country names
        
    Raises:
        Exception: If database query fails
    """
    try:
        logger.info("Attempting to fetch unique countries from database")
        db = get_mongodb_connection()
        collection = db[settings.MONGODB_COLLECTION_NAME]
        
        # Use distinct() to get unique country names
        countries = collection.distinct(
            "msbm_country_full_name",
            {"msbm_country_full_name": {"$exists": True, "$ne": None}}
        )
        
        # Sort the countries alphabetically
        countries.sort()
        
        logger.info(f"Successfully retrieved {len(countries)} unique countries")
        logger.info(f"Countries retrieved: {countries}")
        return countries
        
    except Exception as e:
        logger.warning(f"Error fetching unique countries: {str(e)}")
        return []



def search_articles(
    categories: Optional[List[str]] = None,
    countries: Optional[List[str]] = "Jamaica",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    page_size: int = 10
) -> Dict[str, Any]:
    """
    Search articles with filters for categories, countries, and date range.
    
    Args:
        categories: Optional list of categories to filter by
        countries: Optional list of countries to filter by
        start_date: Optional start date in ISO format
        end_date: Optional end date in ISO format
        page: Page number for pagination
        page_size: Number of items per page
        
    Returns:
        Dict containing:
            - articles: List of articles matching the criteria
            - total: Total number of matching articles
            - page: Current page number
            - total_pages: Total number of pages
    """
    try:
        logger.info("Starting article search with parameters:")
        logger.info(f"Categories received in search_articles: {categories}")
        logger.info(f"Countries received in search_articles: {countries}")
        logger.info(f"Date Range: {start_date} to {end_date}")
        logger.info(f"Page: {page}, Page Size: {page_size}")
        
        db = get_mongodb_connection()
        collection = db[settings.MONGODB_COLLECTION_NAME]
        logger.info(f"Connected to collection: {settings.MONGODB_COLLECTION_NAME}")
        
        # Convert date strings to datetime objects
        start_date_obj = datetime.fromisoformat(start_date.replace('Z', '')) if start_date else None
        end_date_obj = datetime.fromisoformat(end_date.replace('Z', '')) if end_date else None
        
        # Build the query using the specified structure
        query = {
            "msbm_category": {"$in": categories} if categories else {"$exists": True},
            "msbm_country_full_name": {"$in": countries} if countries else {"$exists": True},
            "published_date": {
                "$gte": start_date_obj.strftime("%Y-%m-%d") if start_date_obj else "1900-01-01",
                "$lte": end_date_obj.strftime("%Y-%m-%d") if end_date_obj else "2100-12-31"
            },
            "msbm_caribbean_article": "True"
        }
        
        logger.info(f"Built MongoDB query: {query}")
        
        # Get total count for pagination
        total_articles = collection.count_documents(query)
        logger.info(f"Total matching articles: {total_articles}")
        
        # Log the projection fields we're requesting
        projection = {
            "_id": 0,
            "title": 1,
            "link": 1,
            "domain_url": 1,
            "published_date": 1,
            "msbm_country_full_name": 1,
            "msbm_category": 1,
            "msbm_llm_summary": 1
        }
        logger.info("Projections Loaded")
        
        # Get paginated results
        skip = (page - 1) * page_size
        articles = list(collection.find(query, projection).skip(skip).limit(page_size))
        
        logger.info(f"Retrieved {len(articles)} articles for current page")
        
        # Process articles
        processed_articles = []
        for article in articles:
            try:
                # Format date
                if 'published_date' in article:
                    try:
                        date_obj = datetime.strptime(article['published_date'], '%Y-%m-%d')
                        article['published_date'] = date_obj.strftime('%Y-%m-%d')
                    except ValueError:
                        try:
                            date_obj = datetime.strptime(article['published_date'], '%Y-%m-%d %H:%M:%S')
                            article['published_date'] = date_obj.strftime('%Y-%m-%d')
                        except ValueError:
                            article['published_date'] = article.get('published_date', 'Date not available')
                
                # Set media source
                article['media_source'] = article.get('domain_url', 'Source not available')
                if article['media_source'] != 'Source not available':
                    source = article['media_source']
                    source = source.replace('http://', '').replace('https://', '').replace('www.', '')
                    source = source.rstrip('/')
                    article['media_source'] = source
                
                processed_articles.append(article)
                
            except Exception as e:
                logger.warning(f"Error processing article: {str(e)}")
                continue
        
        return {
            "articles": processed_articles,
            "total": total_articles,
            "page": page,
            "total_pages": (total_articles + page_size - 1) // page_size
        }
        
    except Exception as e:
        logger.warning(f"Search operation failed: {str(e)}", exc_info=True)
        raise

def get_saved_dashboards():
    """
    Retrieves saved dashboards from MongoDB.
    
    Returns:
        list: List of dashboard names and their IDs
    """
    try:
        logger.info("Fetching saved dashboards")
        db = get_mongodb_connection()
        collection = db['dashboards']
        
        # Get dashboards with only necessary fields and convert ObjectId to string
        dashboards = []
        for dashboard in collection.find({}):
            # Convert ObjectId to string and only include necessary fields
            dashboard_data = {
                "dashboard_name": dashboard.get("dashboard_name", "Unnamed Dashboard"),
                "_id": str(dashboard["_id"]),  # Convert ObjectId to string
                "selected_keywords": dashboard.get("selected_keywords", {}),
                "selected_countries": dashboard.get("selected_countries", {}),
                "created_at": dashboard.get("created_at", datetime.now().isoformat())
            }
            dashboards.append(dashboard_data)
        
        logger.info(f"Retrieved {len(dashboards)} dashboards")
        return dashboards
        
    except Exception as e:
        logger.warning(f"Error fetching dashboards: {str(e)}")
        raise

def save_dashboard(
    dashboard_name: str,
    selected_keywords: List[str],
    selected_countries: List[str],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Save a new dashboard to MongoDB.
    
    Args:
        dashboard_name: Name of the dashboard
        selected_keywords: List of selected keywords/categories
        selected_countries: List of selected countries
        start_date: Optional start date in ISO format
        end_date: Optional end date in ISO format
        
    Returns:
        dict: The saved dashboard document
    """
    try:
        logger.info(f"Saving dashboard: {dashboard_name}")
        db = get_mongodb_connection()
        collection = db['dashboards']
        
        # Create dashboard document
        dashboard = {
            "dashboard_name": dashboard_name,
            "selected_keywords": selected_keywords,
            "selected_countries": selected_countries,
            "start_date": start_date,
            "end_date": end_date,
            "created_at": datetime.now().isoformat()
        }
        
        # Insert dashboard
        result = collection.insert_one(dashboard)
        
        # Get the inserted document
        saved_dashboard = collection.find_one({"_id": result.inserted_id})
        
        # Convert ObjectId to string for JSON serialization
        saved_dashboard["_id"] = str(saved_dashboard["_id"])
        
        logger.info(f"Successfully saved dashboard with ID: {saved_dashboard['_id']}")
        return saved_dashboard
        
    except Exception as e:
        logger.warning(f"Error saving dashboard: {str(e)}")
        raise

def update_dashboard_name(dashboard_id: str, new_name: str) -> Optional[Dict[str, Any]]:
    """
    Update a dashboard's name in MongoDB.
    
    Args:
        dashboard_id: ID of the dashboard to update
        new_name: New name for the dashboard
        
    Returns:
        dict: The updated dashboard document or None if not found
    """
    try:
        logger.info(f"Updating dashboard {dashboard_id} with new name: {new_name}")
        db = get_mongodb_connection()
        collection = db['dashboards']
        
        # Convert string ID to ObjectId
        from bson import ObjectId
        object_id = ObjectId(dashboard_id)
        
        # Update the dashboard
        result = collection.find_one_and_update(
            {"_id": object_id},
            {"$set": {"dashboard_name": new_name}},
            return_document=True
        )
        
        if result:
            # Convert ObjectId to string for JSON serialization
            result["_id"] = str(result["_id"])
            logger.info(f"Successfully updated dashboard name")
            return result
        else:
            logger.warning(f"No dashboard found with ID: {dashboard_id}")
            return None
            
    except Exception as e:
        logger.warning(f"Error updating dashboard name: {str(e)}")
        raise
