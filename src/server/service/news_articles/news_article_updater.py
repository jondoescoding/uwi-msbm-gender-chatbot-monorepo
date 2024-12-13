# Python built-in imports
import json
import sys
import time
from datetime import datetime, timedelta

# Third-party imports
from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError
from pydantic import BaseModel, Field, model_validator

# Project-specific imports
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.messages.ai import AIMessage
from news_articles.news_article_collector import COUNTRIES
from backend.core.config import MongoDBConnections, logger, NEWS_API_KEY
from backend.service.llm_service import Groq, OpenAI
from newscatcherapi_client import Newscatcher, ApiException

def update_country_full_names():
    """
    Updates all documents in the summaries collection by adding a 'country_full_name' field
    based on the existing 'country' code.
    """
    try:
        # Initialize MongoDB connection
        mongodb = MongoDBConnections()
        client = MongoClient(mongodb.MONGODB_CONNECTION_STRING)
        db = client[mongodb.MONGODB_DB_NAME]
        
        # Use the MongoDB client
        collection = db['articles']

        # Define a dictionary mapping country codes to full names
        country_map = {
            'AG': 'Antigua and Barbuda', 'AI': 'Anguilla', 'AW': 'Aruba',
            'BB': 'Barbados', 'BM': 'Bermuda', 'BQ': 'Bonaire',
            'BS': 'Bahamas', 'BZ': 'Belize', 'CU': 'Cuba',
            'CW': 'Curaçao', 'DM': 'Dominica', 'DO': 'Dominican Republic',
            'GD': 'Grenada', 'GP': 'Guadeloupe', 'HT': 'Haiti',
            'JM': 'Jamaica', 'KN': 'Saint Kitts and Nevis', 'KY': 'Cayman Islands',
            'LC': 'Saint Lucia', 'PR': 'Puerto Rico', 'SX': 'Sint Maarten',
            'TC': 'Turks and Caicos Islands', 'TT': 'Trinidad and Tobago',
            'VC': 'Saint Vincent and the Grenadines', 'VG': 'British Virgin Islands',
            'VI': 'U.S. Virgin Islands'
        }

        # Update all documents in the collection
        result = collection.update_many(
            {},
            [
                {
                    "$set": {
                        "msbm_country_full_name": {
                            "$switch": {
                                "branches": [
                                    {"case": {"$eq": ["$country", code]}, "then": name}
                                    for code, name in country_map.items()
                                ],
                                "default": "Unknown"
                            }
                        }
                    }
                }
            ]
        )

        logger.info(f"Modified {result.modified_count} documents")

    except Exception as e:
        logger.error(f"An error occurred in update_country_full_names: {e}")
    finally:
        client.close()

def update_summaries_and_categorize():
    """
    Main function to update summaries with categories and categorize uncategorized summaries.
    """
    try:
        # Initialize MongoDB connection
        mongo_conn = MongoDBConnections()
        client = MongoClient(mongo_conn.MONGODB_CONNECTION_STRING)
        db = client[mongo_conn.MONGODB_DB_NAME]
        
        articles_collection = db['articles']
        summaries_collection = db['summaries']
        
        def update_summaries_with_categories():
            """
            Update summaries with categories from matching articles using bulk operations.
            """
            try:
                bulk_operations = []
                for summary in summaries_collection.find():
                    matching_article = articles_collection.find_one({"link": summary["link"]})
                    if matching_article and "category" in matching_article:
                        bulk_operations.append(
                            UpdateOne(
                                {"_id": summary["_id"]},
                                {"$set": {"category": matching_article["category"]}}
                            )
                        )
                
                if bulk_operations:
                    result = summaries_collection.bulk_write(bulk_operations)
                    logger.info(f"Updated {result.modified_count} summaries with categories")
            except BulkWriteError as bwe:
                logger.error(f"Bulk write error in update_summaries_with_categories: {bwe.details}")
            except Exception as e:
                logger.error(f"An error occurred in update_summaries_with_categories: {e}")
        
        def categorize_uncategorized_summaries():
            """
            Categorize summaries that don't have a matching article using keyword matching.
            """
            try:
                with open('src/topics.json', 'r') as f:
                    topics = json.load(f)
                
                bulk_operations = []
                for summary in summaries_collection.find({"category": {"$exists": False}}):
                    category = categorize_summary(summary['summary'], topics)
                    bulk_operations.append(
                        UpdateOne(
                            {"_id": summary["_id"]},
                            {"$set": {"category": category}}
                        )
                    )
                
                if bulk_operations:
                    result = summaries_collection.bulk_write(bulk_operations)
                    logger.info(f"Categorized {result.modified_count} uncategorized summaries")
            except BulkWriteError as bwe:
                logger.error(f"Bulk write error in categorize_uncategorized_summaries: {bwe.details}")
            except Exception as e:
                logger.error(f"An error occurred in categorize_uncategorized_summaries: {e}")
        
        def categorize_summary(summary_text, topics):
            """
            Categorize a summary based on keyword matching with topics.
            """
            for topic in topics:
                keywords = topic['research_topic'] if isinstance(topic['research_topic'], list) else [topic['research_topic']]
                if any(keyword.lower() in summary_text.lower() for keyword in keywords):
                    return topic['research_topic'][0] if isinstance(topic['research_topic'], list) else topic['research_topic']
            return "Uncategorized"
        
        # Execute the functions
        update_summaries_with_categories()
        categorize_uncategorized_summaries()
    
    except Exception as e:
        logger.error(f"An error occurred in update_summaries_and_categorize: {e}")
    finally:
        client.close()

def update_uncategorized_categories():
    """
    Main function to update uncategorized categories in the database.
    """
    try:
        # Initialize MongoDB connection
        mongo_conn = MongoDBConnections()
        client = MongoClient(mongo_conn.MONGODB_CONNECTION_STRING)
        db = client[mongo_conn.MONGODB_DB_NAME]
        summaries_collection = db['summaries']

        # Load topics from JSON file
        with open('src/topics.json', 'r') as f:
            topics = json.load(f)

        def create_categorization_chain():
            """
            Creates and returns the LCEL chain for categorization.
            """
            prompt = ChatPromptTemplate.from_template(
                "Categorize the following summary into one of these categories: {categories}. "
                "You MUST choose one of the given categories.\n\nSummary: {summary}"
            )
            model = Groq.groq70b  # Using groq70b model
            output_parser = StrOutputParser()

            return (
                {"summary": RunnablePassthrough(), "categories": lambda _: ", ".join([t['research_topic'] if isinstance(t['research_topic'], str) else ", ".join(t['research_topic']) for t in topics])}
                | prompt
                | model
                | output_parser
            )

        def process_uncategorized_summaries(chain):
            """
            Processes uncategorized summaries and prepares bulk updates.
            """
            uncategorized_summaries = summaries_collection.find({"category": "Uncategorized"})
            bulk_updates = []

            for summary in uncategorized_summaries:
                try:
                    new_category = chain.invoke(summary['summary'])
                    
                    # Ensure the new category is in the list of valid categories
                    valid_categories = [t['research_topic'] if isinstance(t['research_topic'], str) else t['research_topic'][0] for t in topics]
                    if new_category not in valid_categories:
                        logger.warning(f"Invalid category '{new_category}' for summary {summary['_id']}. Skipping update.")
                        continue

                    # Update summary
                    bulk_updates.append(UpdateOne(
                        {"_id": summary['_id']},
                        {"$set": {"category": new_category}}
                    ))
                    
                    logger.info(f"Prepared update for summary {summary['_id']}: new category '{new_category}'")
                    
                    # Sleep for 3 seconds to avoid rate limiting
                    time.sleep(3)
                except Exception as e:
                    logger.error(f"Error processing summary {summary['_id']}: {str(e)}")

            return bulk_updates

        def execute_bulk_updates(bulk_updates):
            """
            Executes bulk updates on the database.
            """
            if bulk_updates:
                try:
                    result = summaries_collection.bulk_write(bulk_updates, ordered=False)
                    logger.info(f"Updated {result.modified_count} documents")
                except BulkWriteError as bwe:
                    logger.error(f"Bulk update error: {bwe.details}")
            else:
                logger.info("No updates to perform")

        # Main execution flow
        chain = create_categorization_chain()
        bulk_updates = process_uncategorized_summaries(chain)
        execute_bulk_updates(bulk_updates)

    except Exception as e:
        logger.error(f"An error occurred in update_uncategorized_categories: {str(e)}")
    finally:
        client.close()
        logger.info("Database connection closed")

class CaribbeanArticle(BaseModel):
    is_caribbean: str = Field(description="Whether the article is about a Caribbean country. Can ONLY be True or False.")

    @model_validator(mode='after')
    def check_is_caribbean_value(self) -> 'CaribbeanArticle':
        if not isinstance(self.is_caribbean, str):
            raise ValueError("is_caribbean must be a string value (True or False)")
        return self

def update_article_type():
    logger.info("Starting update_article_type process")
    
    # Connect to MongoDB
    client = MongoClient(MongoDBConnections.MONGODB_CONNECTION_STRING)
    db = client[MongoDBConnections.MONGODB_DB_NAME]
    collection = db['articles']  # New collection name
    logger.info("Connected to MongoDB")

    # Get articles that haven't been processed yet
    unprocessed_articles = collection.find({
        'msbm_caribbean_article': {'$exists': False},
        'msbm_llm_summary': {'$exists': True, '$ne': None}
    })
    total_articles = collection.count_documents({
        'msbm_caribbean_article': {'$exists': False},
        'msbm_llm_summary': {'$exists': True, '$ne': None}
    })
    logger.info(f"Fetched {total_articles} unprocessed articles from the database")

    # Initialize GPT-4 model
    openai = OpenAI()
    gpt4 = openai.get_model("gpt4o")
    logger.info("Initialized GPT-4 model")

    # Set up the parser
    parser = PydanticOutputParser(pydantic_object=CaribbeanArticle)
    logger.info("Set up PydanticOutputParser")

    # Create the prompt template
    prompt = PromptTemplate(
        template="""
        <background_information>
        You are an expert at determining if an article is about a Caribbean country.
        The list of Caribbean countries is: {countries}
        </background_information>

        <objective>
        Determine if the following article summary is ONLY about news from a Caribbean country listed above.
        </objective>

        <constraints>
        {format_instructions}
        </constraints>

        <article_summary>
        {article_summary}
        </article_summary>
        """,
        input_variables=["countries", "article_summary"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    logger.info("Created prompt template")

    bulk_operations = []
    processed_count = 0
    for article in unprocessed_articles:
        processed_count += 1
        logger.info(f"Processing article {processed_count}/{total_articles} (ID: {article['_id']})")
        
        # Prepare the prompt
        formatted_prompt = prompt.format(
            countries=COUNTRIES,
            article_summary=article['msbm_llm_summary']
        )
        logger.debug("Formatted prompt for article")

        # Get the response from the model
        response = gpt4.invoke(formatted_prompt)
        logger.debug("Received response from GPT-4 model")

        # Extract the content from AIMessage if necessary
        if isinstance(response, AIMessage):
            response_content = response.content
        else:
            response_content = response
        logger.debug("Extracted response content")

        # Parse the response
        parsed_response = parser.parse(response_content)
        logger.debug(f"Parsed response: {parsed_response.is_caribbean}")

        bulk_operations.append(
            UpdateOne(
                {'_id': article['_id']},
                {'$set': {'msbm_caribbean_article': parsed_response.is_caribbean}}
            )
        )

        # Perform bulk update in batches of 1000
        if len(bulk_operations) >= 1000:
            try:
                result = collection.bulk_write(bulk_operations)
                logger.info(f"Bulk update: processed and updated {result.modified_count} articles")
            except BulkWriteError as bwe:
                logger.error(f"Bulk write error: {bwe.details}")
            bulk_operations = []

        # Log progress every 100 articles
        if processed_count % 100 == 0:
            logger.info(f"Progress: {processed_count}/{total_articles} articles processed")

    # Process any remaining operations
    if bulk_operations:
        try:
            result = collection.bulk_write(bulk_operations)
            logger.info(f"Final bulk update: processed and updated {result.modified_count} articles")
        except BulkWriteError as bwe:
            logger.error(f"Bulk write error: {bwe.details}")

    client.close()
    logger.info(f"Article type update process completed. Total articles processed: {processed_count}")

def update_article_source():
    """
    Updates the 'source_name' field for articles in the MongoDB collection where 'msbm_caribbean_article' is 'True'.
    
    This function connects to a MongoDB collection, retrieves articles with 'msbm_caribbean_article' set to 'True',
    uses the Newscatcher API to find the source name for each article's link, and updates the MongoDB documents
    with the retrieved source name.
    """
    logger.info("Starting update_article_source process")

    # Connect to MongoDB
    client = MongoClient(MongoDBConnections.MONGODB_CONNECTION_STRING)
    db = client[MongoDBConnections.MONGODB_DB_NAME]
    collection = db['articles']
    logger.info("Connected to MongoDB")

    # Initialize Newscatcher client
    newscatcher = Newscatcher(api_key=NEWS_API_KEY)

    # Calculate date range
    today = datetime.now().strftime('%Y-%m-%d')
    a_year_ago = (datetime.now() - timedelta(days=365*2)).strftime('%Y-%m-%d')

    # Find articles with msbm_caribbean_article set to "True"
    articles = collection.find({'msbm_caribbean_article': 'True'})
    total_articles = collection.count_documents({'msbm_caribbean_article': 'True'})
    logger.info(f"Fetched {total_articles} articles with msbm_caribbean_article set to 'True'")

    bulk_operations = []
    for article in articles:
        retries = 0
        max_retries = 5
        backoff_factor = 2
        while retries < max_retries:
            try:
                # Use Newscatcher SDK to get the source name
                response = newscatcher.search_link.post(
                    links=[article['link']],
                    from_=today,
                    to_=a_year_ago
                )
                if response and response.articles:
                    name_source = response.articles[0].name_source
                    # Prepare the update operation
                    bulk_operations.append(
                        UpdateOne(
                            {'_id': article['_id']},
                            {'$set': {'source_name': name_source}}
                        )
                    )
                elif response and response.status == "We couldn't find that article by link, try searching it by the title on the search endpoint.":
                    # Attempt to search by ID
                    id_response = newscatcher.search_link.post(ids=str(article['_id']))
                    if id_response and id_response.articles:
                        name_source = id_response.articles[0].name_source
                        # Prepare the update operation
                        bulk_operations.append(
                            UpdateOne(
                                {'_id': article['_id']},
                                {'$set': {'source_name': name_source}}
                            )
                        )
                    else:
                        logger.warning(f"No source name found for article ID: {article['_id']} by ID search")
                break  # Exit the retry loop if successful

            except ApiException as e:
                if e.status == 429:  # Too many requests
                    retries += 1
                    sleep_time = backoff_factor ** retries
                    logger.warning(f"Rate limit hit for article ID {article['_id']}. Retrying in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"Error processing article ID {article['_id']}: {str(e)}")
                    break

    # Execute bulk updates
    if bulk_operations:
        try:
            result = collection.bulk_write(bulk_operations)
            logger.info(f"Updated {result.modified_count} documents with source names")
        except BulkWriteError as bwe:
            logger.error(f"Bulk update error: {bwe.details}")
    else:
        logger.info("No updates to perform")

    client.close()
    logger.info("Article source update process completed")

def main():
    """
    Main function that acts as a CLI terminal interface.
    """
    while True:
        print("\nNews Article Management CLI")
        print("1. Update Country Full Names")
        print("2. Update Summaries and Categorize")
        print("3. Update Uncategorized Categories")
        print("4. Update Article Type")
        print("5. Update Article Source")  # New option added
        print("6. Exit")
        
        choice = input("Enter your choice (1-6): ")
        
        try:
            match choice:
                case "1":
                    update_country_full_names()
                case "2":
                    update_summaries_and_categorize()
                case "3":
                    update_uncategorized_categories()
                case "4":
                    update_article_type()
                case "5":
                    update_article_source()  # Call the new function
                case "6":
                    logger.info("Exiting the program. Goodbye!")
                    sys.exit(0)
                case _:
                    print("Invalid choice. Please try again.")
        except Exception as e:
            logger.error(f"An error occurred in main: {e}")

if __name__ == "__main__":
    main()
