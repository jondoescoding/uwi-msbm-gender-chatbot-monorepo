from pydantic import BaseModel, Field, field_validator
from typing import List


class ArticleMetadata(BaseModel):
    """Pydantic model for the metadata fields of an article."""
    
    # Main article data being used
    title: List[str] = Field(description="The title(s) of the article(s).", default_factory=list)
    links: List[str] = Field(description="A list of https URL(s) of the article(s).", default_factory=list)
    name_source: List[str] = Field(description="A list of source(s) used to compose the essay.", default_factory=list)
    date: List[str] = Field(description="The published date(s) of the article(s).", default_factory=list)
    
    # Additional metadata fields with proper defaults and validation
    author: List[str] = Field(
        description="Author(s) of the article(s).",
        default_factory=list
    )
    authors: List[str] = Field(
        description="List of authors for each article(s).",
        default_factory=list
    )
    description: List[str] = Field(description="Brief descriptions of the article(s).", default_factory=list)
    domain_url: List[str] = Field(description="Base domain URLs of the article(s).", default_factory=list)
    full_domain_url: List[str] = Field(description="Complete domain URLs of the article(s).", default_factory=list)
    language: List[str] = Field(description="Language used within the article(s).", default_factory=list)
    parent_url: List[str] = Field(description="Parent URLs of the article(s).", default_factory=list)
    rights: List[str] = Field(description="Copyright information for the article(s).", default_factory=list)
    word_count: List[int] = Field(description="Word counts of the article(s).", default_factory=list)
    msbm_country_full_name: List[str] = Field(description="The full name(s) of the country which the article(s) are about.", default_factory=list)
    msbm_category: List[str] = Field(description="The gender category/topic of the article(s).", default_factory=list)


    @field_validator('author', 'authors', mode='before')
    @classmethod
    def handle_none_values(cls, v):
        """Handle None values and flatten author lists"""
        if v is None:
            return []
        
        def flatten_and_join(item):
            if isinstance(item, list):
                # Filter out None/empty values and join with comma
                return ', '.join(filter(None, item))
            return item or ''
        
        if isinstance(v, list):
            return [flatten_and_join(item) for item in v]
        return [flatten_and_join(v)]

    class Config:
        """Configuration for the Pydantic model"""
        validate_assignment = True
        arbitrary_types_allowed = True
        from_attribute = True


class Articles(BaseModel):
    """Pydantic model containing the metadata for the article and its content"""
    content: str = Field(description="Full article's content")
    metadata: dict = Field(description="Relevant non-empty article metadata")
    
    class Config:
        from_attributes = True