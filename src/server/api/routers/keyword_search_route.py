"""
Keyword Search Router Module
--------------------------
This module handles all keyword search related routes for the news article application.
It provides endpoints for retrieving country data and performing keyword searches.

Routes:
    - GET /countries: Retrieves list of unique countries
    - GET /search: Search articles with filters
    - GET /dashboards: Retrieves saved dashboards
    - POST /dashboards: Save a new dashboard
    - PATCH /dashboards/{dashboard_id}: Update dashboard name
"""

from fastapi import APIRouter, HTTPException, Query, Body
from src.server.core.logging import setup_logger
from src.server.service.search_service import (
    get_unique_countries, 
    search_articles, 
    get_saved_dashboards,
    save_dashboard,
    update_dashboard_name
)
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

# Configure logging using our custom logger
logger = setup_logger("server.api.routers.keyword_search_route")

# Pydantic models
class DashboardCreate(BaseModel):
    selected_keywords: List[str]
    selected_countries: List[str]
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class DashboardUpdate(BaseModel):
    dashboard_name: str

router = APIRouter(tags=["keyword-search"])

@router.get("/countries")
async def get_countries():
    """
    Retrieves a list of unique countries from the database.
    
    Returns:
        dict: Contains list of country names under 'countries' key
        
    Raises:
        HTTPException: If database query fails
    """
    logger.info("Received request for unique countries")
    try:
        countries = get_unique_countries()
        logger.info(f"Successfully retrieved {len(countries)} countries")
        return {"countries": countries}
    except Exception as e:
        error_msg = f"Failed to retrieve countries: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/search")
async def search_news_articles(
    category: Optional[List[str]] = Query(default=None, alias="category[]"),
    country: Optional[List[str]] = Query(default=None, alias="country[]"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Items per page")
):
    """
    Search articles with filters for categories, countries, and date range.
    """
    logger.info("Received search request")
    logger.info(f"Raw category parameter: {category}")
    logger.info(f"Raw country parameter: {country}")
    logger.info(f"Raw date parameters: start={start_date}, end={end_date}")
    
    try:
        # Validate dates if provided
        if start_date:
            datetime.fromisoformat(start_date)
        if end_date:
            datetime.fromisoformat(end_date)
        
        # Ensure category and country are lists
        categories = category if category else []
        countries = country if country else []
        
        logger.info(f"Processed categories: {categories}")
        logger.info(f"Processed countries: {countries}")
            
        results = search_articles(
            categories=categories,
            countries=countries,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size
        )
        
        logger.info(f"Search completed successfully. Found {results['total']} articles")
        return results
        
    except ValueError as e:
        error_msg = f"Invalid date format: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        error_msg = f"Failed to search articles: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/dashboards")
async def get_dashboards():
    """
    Retrieves a list of saved dashboards from the database.
    
    Returns:
        dict: Contains list of dashboard names and their IDs
        
    Raises:
        HTTPException: If database query fails
    """
    logger.info("Received request for saved dashboards")
    try:
        dashboards = get_saved_dashboards()
        logger.info(f"Successfully retrieved {len(dashboards)} dashboards")
        return {"dashboards": dashboards}
    except Exception as e:
        error_msg = f"Failed to retrieve dashboards: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/dashboards")
async def create_dashboard(dashboard: DashboardCreate):
    """
    Save a new dashboard with the selected filters.
    
    Args:
        dashboard: Dashboard creation data including selected keywords and countries
        
    Returns:
        dict: Contains the created dashboard information
        
    Raises:
        HTTPException: If saving fails or parameters are invalid
    """
    logger.info("Received request to save dashboard")
    try:
        if not dashboard.selected_keywords or not dashboard.selected_countries:
            raise ValueError("Both keywords and countries must be provided")
            
        # Generate dashboard name from selections
        keywords_str = " & ".join(dashboard.selected_keywords)
        countries_str = " & ".join(dashboard.selected_countries)
        current_year = datetime.now().year
        dashboard_name = f"Analyzing {keywords_str} in {countries_str} - {current_year}"
        
        # Save dashboard
        saved_dashboard = save_dashboard(
            dashboard_name=dashboard_name,
            selected_keywords=dashboard.selected_keywords,
            selected_countries=dashboard.selected_countries,
            start_date=dashboard.start_date,
            end_date=dashboard.end_date
        )
        
        logger.info(f"Successfully saved dashboard: {dashboard_name}")
        return {"dashboard": saved_dashboard}
        
    except ValueError as e:
        error_msg = str(e)
        logger.error(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        error_msg = f"Failed to save dashboard: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.patch("/dashboards/{dashboard_id}")
async def update_dashboard(dashboard_id: str, update_data: DashboardUpdate):
    """
    Update a dashboard's name.
    
    Args:
        dashboard_id: ID of the dashboard to update
        update_data: New dashboard name
        
    Returns:
        dict: The updated dashboard
        
    Raises:
        HTTPException: If update fails or dashboard not found
    """
    logger.info(f"Received request to update dashboard {dashboard_id}")
    try:
        updated_dashboard = update_dashboard_name(
            dashboard_id=dashboard_id,
            new_name=update_data.dashboard_name
        )
        
        if not updated_dashboard:
            raise HTTPException(status_code=404, detail="Dashboard not found")
            
        logger.info(f"Successfully updated dashboard: {dashboard_id}")
        return {"dashboard": updated_dashboard}
        
    except Exception as e:
        error_msg = f"Failed to update dashboard: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
