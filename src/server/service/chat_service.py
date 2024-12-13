from typing import Dict, List, Any
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from pydantic import BaseModel, Field
from server.core.logging import setup_logger
from server.service.astra_service import AstraService
from server.service.llm_service import OpenAI
from server.models.article_model import ArticleMetadata, Articles
from server.models.chat_model import LLMResponse
from langchain.memory import ConversationBufferMemory
from langchain.callbacks.tracers import LangChainTracer
from datetime import datetime
import pytz

logger = setup_logger(name=__name__)

class QuestionClassification(BaseModel):
    """Model for classifying if a question is gender-related."""
    is_gender_related: bool = Field(description="Whether the question is related to gender issues")
    explanation: str = Field(description="Brief explanation of the classification")
    topics: List[str] = Field(description="Specific gender-related topics identified in the question", default_factory=list)

class ChatService:
    """Service for handling chat operations"""
    
    def __init__(self):
        """Initialize chat service with required dependencies"""
        self.astra_service = AstraService()
        self.llm_service = OpenAI()
        self.llm = self.llm_service.get_model(name="gpt4o")
        self.memory = ConversationBufferMemory()
        self.tracer = LangChainTracer()
        
        # Configure classifier prompt
        self.classifier_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a question classifier focused on identifying gender-related queries.
            Analyze the question for:
            1. Gender-related topics (MUST classify into A SINGLE categories if gender-related):
               - LGBTQ+ Rights and Issues
               - Gender Equality and Discrimination
               - Women's Rights and Empowerment
               - Men's Issues and Masculinity
               - Gender-Based Violence
               - Gender in Education
               - Gender in Workplace
               - Gender Policies and Legislation
               - Gender and Health
               - Gender and Media Representation
               - Gender and Sports
               - Gender and Culture
            2. Geographic focus:
               - Caribbean region specifics
               - Country-specific mentions
            3. Time relevance:
               - Specific year mentions
               - Current news
               - Historical context
               - Future developments"""),
            ("human", "{question}")
        ])
        
        # Configure enhanced gender-related prompt template
        self.gender_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a friendly Caribbean Gender Expert having a warm, engaging conversation.
            
            CRITICAL RULES:
            1. STRICT 300-WORD LIMIT - responses must be concise and focused
            2. NEVER start responses with phrases about limitations or missing information
            3. ALWAYS begin naturally and positively, like:
               - "In Jamaica's vibrant gender landscape of 2023..."
               - "Throughout 2023, Jamaica's gender initiatives have shown..."
               - "The Ministry of Gender has been actively shaping..."
            
            Key Guidelines:
            1. Concise Yet Informative:
               - Get to the point quickly
               - Focus on most relevant information
               - Use clear, direct language
               - Prioritize key insights
            
            2. Response Structure (within 300 words):
               - 1-2 sentences for opening (natural, engaging start)
               - 2-3 paragraphs for main content
               - 1 sentence for conclusion
               - Keep paragraphs short and focused
            
            3. Information Priority:
               - Lead with most significant gender developments
               - Include only the most relevant examples
               - Focus on concrete actions and outcomes
               - Highlight direct gender implications
            
            4. Source Integration:
               - Mention only the most relevant sources
               - Integrate citations naturally
               - Keep source mentions brief
            
            Remember:
            - Stay within 300-word limit
            - Keep tone friendly but concise
            - Focus on most impactful information"""),
            ("system", "Available sources metadata: Titles: {titles}, Links: {links}, Sources: {sources}, Dates: {dates}"),
            ("system", "Previous conversation: {chat_history}"),
            ("system", "These are the news articles we have found related to the question being asked: {content}"),
            ("human", "{question}")
        ])
        
        # Configure non-gender prompt template
        self.general_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful AI assistant. For non-gender related questions:
            - Provide clear, concise answers
            - Use your general knowledge
            - Do not include sources in your response
            - Keep the tone conversational but professional"""),
            ("system", "Previous conversation: {chat_history}"),
            ("human", "{question}")
        ])

    def _match_gender_topic(self, question: str) -> List[str]:
        """
        Match a user's question against predefined gender topics from topics.json.
        Returns only the single most relevant topic based on exact phrase matching first,
        then falling back to keyword matching if needed.
        
        This method performs a deterministic matching of the input question against a set of
        predefined gender topics and their definitions. It uses a keyword-based approach to
        identify relevant gender topics.
        
        Args:
            question (str): The user's input question to be analyzed.
            
        Returns:
            List[str]: A list of matched gender topic names. Empty list if no matches found.
            
        Example:
            >>> service._match_gender_topic("What is the latest news about gender violence?")
            ["Gender Based Violence"]
            
        Note:
            - The matching is case-insensitive
            - Topics are loaded from src/server/data/topics.json
            - Matches are found both in topic names and their definitions
            - Multiple topics can be matched for a single question
        
        Raises:
            FileNotFoundError: If topics.json file is not found
            json.JSONDecodeError: If topics.json is not properly formatted
        """
        import json
        
        logger.info(f"🔍 Starting topic matching for question: {question}")
        
        try:
            # Load topics from JSON file
            logger.info("Loading topics from topics.json")
            with open("src/server/data/topics.json", "r") as f:
                topics = json.load(f)
            logger.info(f"Successfully loaded {len(topics)} topics from topics.json")
        
            question = question.lower()
            logger.info(f"Normalized question for matching: {question}")
            
            # First try exact phrase matching
            for topic in topics:
                topic_name = topic["research_topic"]
                topic_phrase = topic_name.lower()
                
                # If we find an exact phrase match, return immediately
                if topic_phrase in question:
                    logger.info(f"✅ Found exact phrase match for topic: {topic_name}")
                    return [topic_name]
            
            # If no exact phrase match, try keyword matching with scoring
            best_match = None
            best_score = 0
            
            for topic in topics:
                topic_name = topic["research_topic"]
                logger.info(f"Checking topic: {topic_name}")
                
                # Calculate match score based on keywords
                topic_name_lower = topic_name.lower()
                topic_def = topic["definition"].lower()
                
                # Create a set of key terms from the topic name and definition
                key_terms = set(topic_name_lower.split() + topic_def.split())
                logger.info(f"Generated {len(key_terms)} key terms for topic {topic_name}")
                
                # Calculate score based on number of matching terms
                score = sum(1 for term in key_terms if term in question)
                
                if score > best_score:
                    best_score = score
                    best_match = topic_name
            
            if best_match and best_score > 0:
                logger.info(f"✅ Best matching topic: {best_match} (score: {best_score})")
                return [best_match]
            
            logger.info("❌ No matching topics found")
            return []
                
        except FileNotFoundError as e:
            logger.warning(f"❌ Failed to load topics.json: {str(e)}")
            raise
        except json.JSONDecodeError as e:
            logger.warning(f"❌ Invalid JSON in topics.json: {str(e)}")
            raise
        except Exception as e:
            logger.warning(f"❌ Unexpected error in topic matching: {str(e)}")
            raise

    def _classify_question(self, question: str) -> QuestionClassification:
        """
        Classify if a question is gender-related using a hybrid approach.
        
        This method uses a two-step classification process:
        1. First attempts to match against predefined gender topics from topics.json
        2. Falls back to LLM-based classification if no direct matches are found
        
        The hybrid approach ensures both accuracy and efficiency by using deterministic
        matching where possible and AI-based classification as a fallback.
        
        Args:
            question (str): The user's input question to be classified.
            
        Returns:
            QuestionClassification: A Pydantic model containing:
                - is_gender_related (bool): Whether the question is gender-related
                - explanation (str): Reasoning behind the classification
                - topics (List[str]): Identified gender topics
                
        Example:
            >>> result = service._classify_question("What about gender violence in Jamaica?")
            >>> print(result.is_gender_related)  # True
            >>> print(result.topics)  # ["Gender Based Violence"]
            
        Note:
            - Classification is case-insensitive
            - Multiple topics can be identified for a single question
            - LLM classification is used as a fallback mechanism
            - Logs classification results for monitoring
            
        Raises:
            Exception: If classification fails, returns a default classification
                      with is_gender_related=True as a safe fallback
        """
        logger.info("🔄 Starting question classification process")
        logger.info(f"Input question: {question}")
        
        try:
            # First match against predefined gender topics
            logger.info("Step 1: Attempting direct topic matching")
            matched_topics = self._match_gender_topic(question)
            
            if matched_topics:
                logger.info(f"✅ Direct topic match successful. Topic: {matched_topics[0]}")
                classification = QuestionClassification(
                    is_gender_related=True,
                    explanation=f"Question matches gender topic: {matched_topics[0]}",
                    topics=matched_topics
                )
                logger.info(f"Created classification: {classification}")
                return classification
            
            # If no direct matches, use the LLM classifier as fallback
            logger.info("Step 2: No direct matches found, falling back to LLM classification")
            logger.info("Initializing LLM classification chain")
            
            classification_chain = (
                self.classifier_prompt 
                | self.llm.with_structured_output(QuestionClassification)
            )
            
            logger.info("Invoking LLM classification chain")
            result = classification_chain.invoke({"question": question})
            
            logger.info(f"✅ LLM Classification complete")
            logger.info(f"Is gender related: {result.is_gender_related}")
            logger.info(f"Topics identified: {result.topics}")
            logger.info(f"Full classification result: {result}")
            
            return result
            
        except Exception as e:
            logger.warning(f"❌ Classification failed with error: {str(e)}")
            logger.warning("Falling back to default classification")
            default_classification = QuestionClassification(
                is_gender_related=True, 
                explanation="Classification failed", 
                topics=[]
            )
            logger.info(f"Created default classification: {default_classification}")
            return default_classification

    def get_context_from_vectorstore(self, question: str, classification: QuestionClassification) -> List[Articles]:
        """Enhanced context retrieval using classification results."""
        logger.info(f"Retrieving context for question with topics: {classification.topics}")
        try:
            # Build a more targeted search query
            search_terms = []
            
            # Add topic-specific terms
            for topic in classification.topics:
                if "LGBTQ" in topic or "gay" in topic.lower():
                    search_terms.extend(["LGBTQ", "gay", "lesbian", "transgender", "queer", "sexual orientation"])
                elif "violence" in topic.lower():
                    search_terms.extend(["violence", "abuse", "assault", "harassment"])
                elif "equality" in topic.lower():
                    search_terms.extend(["equality", "discrimination", "rights", "equity"])
                elif "education" in topic.lower():
                    search_terms.extend(["education", "school", "university", "student"])
                elif "workplace" in topic.lower():
                    search_terms.extend(["workplace", "employment", "job", "career"])
            
            # Combine terms into search query
            enhanced_query = f"{question} {' '.join(search_terms)}"
            
            # Adjust search parameters
            k = 5  # Increased from 3-4 to 5 documents
            fetch_k = 50  # Increased from 30 to 50 for larger candidate pool
            lambda_mult = 0.8  # Increased from 0.7 to 0.8 for more relevance focus
            
            # Generate filters
            filters = self.generate_vectorstore_filter(question)
            
            # First try with filters
            docs = self.astra_service.search_documents(
                query=enhanced_query,
                filters=filters,
                k=k,
                fetch_k=fetch_k,
                lambda_mult=lambda_mult
            )
            
            if not docs or len(docs) < 2:
                # If no results or too few, try without filters but with enhanced query
                docs = self.astra_service.search_documents(
                    query=enhanced_query,
                    filters=None,
                    k=k,
                    fetch_k=fetch_k,
                    lambda_mult=lambda_mult
                )
            
            # If still no results, try original query without enhancements
            if not docs:
                docs = self.astra_service.search_documents(
                    query=question,
                    filters=None,
                    k=k,
                    fetch_k=fetch_k,
                    lambda_mult=0.6  # Lower lambda for more diversity in last resort
                )
            
            # Process and deduplicate results
            seen_contents = set()
            structured_contexts = []
            
            for doc in docs:
                if doc.page_content not in seen_contents:
                    seen_contents.add(doc.page_content)
                    filtered_metadata = {
                        k: v for k, v in doc.metadata.items() 
                        if v is not None and v != "" and (not isinstance(v, list) or v)
                    }
                    structured_contexts.append(
                        Articles(
                            content=doc.page_content,
                            metadata=filtered_metadata
                        )
                    )
            
            logger.info(f"Retrieved {len(structured_contexts)} unique documents")
            return structured_contexts
            
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            raise

    async def process_chat_request(self, messages: List[Dict[str, str]], conversation_id: str = None) -> Dict[str, Any]:
        """Process a chat request with enhanced context retrieval."""
        try:
            logger.info("🟩 [Service] Starting chat request processing")
            
            user_message = messages[-1]["content"]
            logger.info(f"🟩 [Service] Processing user message: {user_message}")
            
            # Update chat history
            for msg in messages:
                self.memory.chat_memory.add_message({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # Enhanced classification
            classification = self._classify_question(user_message)
            
            if classification.is_gender_related:
                # Get context with enhanced retrieval
                context_docs = self.get_context_from_vectorstore(user_message, classification)
                context_data = self.process_context(context_docs)
                
                # Prepare input for gender-related response
                chain_input = {
                    "content": context_data["content"],
                    "titles": context_data["metadata"]["title"],
                    "links": context_data["metadata"]["links"],
                    "sources": context_data["metadata"]["name_source"],
                    "dates": context_data["metadata"]["date"],
                    "chat_history": self.memory.chat_memory.messages,
                    "question": user_message
                }
                
                prompt_value = self.gender_prompt.invoke(chain_input)
                response = self.llm.invoke(prompt_value)
                
                result = {
                    "response": response.content,
                    "sources": [
                        {
                            "title": title,
                            "link": link,
                            "source": source,
                            "date": date
                        }
                        for title, link, source, date in zip(
                            context_data["metadata"]["title"],
                            context_data["metadata"]["links"],
                            context_data["metadata"]["name_source"],
                            context_data["metadata"]["date"]
                        )
                    ],
                    "conversation_id": conversation_id or "new_id"
                }
            else:
                # Handle non-gender questions
                chain_input = {
                    "chat_history": self.memory.chat_memory.messages,
                    "question": user_message
                }
                
                prompt_value = self.general_prompt.invoke(chain_input)
                response = self.llm.invoke(prompt_value)
                
                result = {
                    "response": response.content,
                    "sources": [],
                    "conversation_id": conversation_id or "new_id"
                }
            
            logger.info("🟩 [Service] Request processing completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"🔴 [Service] Chat request processing error: {str(e)}", exc_info=True)
            raise

    def process_filters(self, filters: ArticleMetadata) -> dict:
        """Process raw filters into AstraDB query format."""
        logger.info(f"Processing raw filters: {filters}")
        final_filters = {}
        
        # Add filters for each metadata field if present
        if filters.msbm_country_full_name:
            final_filters["msbm_country_full_name"] = {"$in": filters.msbm_country_full_name}
            
        if filters.date:
            try:
                dates = sorted(filters.date)
                final_filters["published_date"] = {
                    "$gte": dates[0],
                    "$lte": dates[-1]
                }
            except Exception as e:
                logger.warning(f"Error processing date range filter: {str(e)}")
            
        if filters.author:
            final_filters["author"] = {"$in": filters.author}
            
        if filters.domain_url:
            final_filters["domain_url"] = {"$in": filters.domain_url}
            
        if filters.language:
            final_filters["language"] = {"$in": filters.language}
            
        if filters.word_count:
            final_filters["word_count"] = {"$in": filters.word_count}
            
        if filters.rights:
            final_filters["rights"] = {"$in": filters.rights}
        
        if filters.title:
            final_filters["title"] = {"$in": filters.title}
            
        if filters.links:
            final_filters["url"] = {"$in": filters.links}
            
        if filters.name_source:
            final_filters["source"] = {"$in": filters.name_source}
        
        # Add msbm_category to filters if present
        if filters.msbm_category:
            final_filters["msbm_category"] = {"$in": filters.msbm_category}
            logger.info(f"Added msbm_category to filters: {filters.msbm_category}")

        # Combine multiple filters with $and if needed
        if len(final_filters) > 1:
            return {"$and": [{k: v} for k, v in final_filters.items()]}
        elif len(final_filters) == 1:
            return final_filters
        return {}

    def generate_vectorstore_filter(self, question: str) -> ArticleMetadata:
        """Generate filters for AstraDB vector store based on question analysis using LCEL."""
        logger.info(f"Generating filters for question: {question}")
        try:
            # First get the topic classification
            classification = self._classify_question(question)
            
            # Extract temporal indicators
            temporal_info = self._extract_temporal_indicators(question)
            
            system_prompt = """You are an expert at analyzing questions to determine filters.
            Given a question, extract any specific metadata that matches these categories:
            
            Extract ONLY:
            - Full country names (if mentioned). So if you see Trinidad it would become Trinidad and Tobago. Do this for ALL countries which may have a double name.
            - Author names (if mentioned)
            - Source domains or URLs (if mentioned)
            - Languages (if mentioned)
            - Word count ranges (if mentioned)
            - Rights/copyright information (if mentioned)
            - Article titles (if mentioned)
            - Source names (if mentioned)
            - Specific URLs or links (if mentioned)"""

            filter_chain = (
                RunnablePassthrough() 
                | ChatPromptTemplate.from_messages([
                    ("system", system_prompt),
                    ("human", "{input}")
                ])
                | self.llm.with_structured_output(ArticleMetadata)
                | (lambda x: self._add_topics_to_metadata(x, classification.topics))
                | (lambda x: self._add_temporal_filter(x, temporal_info))
                | (lambda x: self.process_filters(x))
            )
            
            return filter_chain.invoke({"input": question})
            
        except Exception as e:
            logger.warning(f"Filter generation failed: {str(e)}")
            return {}

    def _add_topics_to_metadata(self, metadata: ArticleMetadata, topics: List[str]) -> ArticleMetadata:
        """Add topics to the metadata object as msbm_category."""
        metadata.msbm_category = topics
        logger.info(f"Added msbm_category to metadata: {topics}")
        return metadata

    def _add_temporal_filter(self, metadata: ArticleMetadata, temporal_info: dict) -> ArticleMetadata:
        """Add temporal information to metadata if present."""
        if temporal_info['is_temporal'] and temporal_info['date_range']:
            metadata.date = list(temporal_info['date_range'])
            logger.info(f"Added temporal filter to metadata: {temporal_info['date_range']}")
        return metadata

    def process_context(self, context_docs: List[Articles]) -> dict:
        """Process context documents into structured data for the LLM."""
        logger.info(f"Processing {len(context_docs)} context documents")
        metadata = {
            "title": [],
            "links": [],
            "name_source": [],
            "date": []
        }
        
        content = []
        for doc in context_docs:
            content.append(doc.content)
            meta = doc.metadata
            metadata["title"].append(meta.get("title", ""))
            metadata["links"].append(meta.get("link", ""))
            metadata["name_source"].append(meta.get("name_source", ""))
            metadata["date"].append(meta.get("published_date", ""))
        
        return {
            "content": "\n\n".join(content),
            "metadata": metadata
        }

    def format_response(self, response: LLMResponse) -> Dict[str, Any]:
        """Format the response for the API"""
        try:
            formatted_response = {
                "answer": response.answer,
                "sources": []
            }
            
            for title, link, source, date in zip(
                response.title or [], 
                response.links or [], 
                response.name_source or [], 
                response.date or []
            ):
                formatted_response["sources"].append({
                    "title": title,
                    "link": link,
                    "source": source,
                    "date": date
                })
                
            return formatted_response
        except Exception as e:
            logger.error(f"Error formatting response: {e}")
            raise

    def _extract_temporal_indicators(self, question: str) -> dict:
        """
        Extract temporal indicators from the question and convert them to date ranges.
        
        Args:
            question (str): The user's question
            
        Returns:
            dict: Dictionary containing temporal information:
                - is_temporal (bool): Whether temporal indicators were found
                - temporal_type (str): 'specific_year', 'latest', 'oldest', or None
                - date_range (tuple): (start_date, end_date) in ISO format
        """
        current_date = datetime.now(pytz.UTC)
        question_lower = question.lower()
        
        # First check for specific year mentions
        import re
        year_pattern = r'\b(19|20)\d{2}\b'  # Matches years from 1900-2099
        year_match = re.search(year_pattern, question)
        
        if year_match:
            specific_year = int(year_match.group())
            start_date = datetime(specific_year, 1, 1, tzinfo=pytz.UTC)
            end_date = datetime(specific_year, 12, 31, tzinfo=pytz.UTC)
            return {
                'is_temporal': True,
                'temporal_type': 'specific_year',
                'date_range': (start_date.isoformat(), end_date.isoformat())
            }
        
        temporal_indicators = {
            'latest': ['latest', 'recent', 'newest', 'current', 'today', 'now', 'this year', 'this month'],
            'oldest': ['oldest', 'earliest', 'first', 'past', 'historical', 'previous']
        }
        
        # Check for other temporal indicators
        for temp_type, indicators in temporal_indicators.items():
            if any(indicator in question_lower for indicator in indicators):
                logger.info(f"Found temporal indicator of type: {temp_type}")
                
                if temp_type == 'latest':
                    start_date = datetime(current_date.year, 1, 1, tzinfo=pytz.UTC)
                    end_date = current_date
                else:
                    start_date = datetime(current_date.year - 1, 1, 1, tzinfo=pytz.UTC)
                    end_date = datetime(current_date.year - 1, 12, 31, tzinfo=pytz.UTC)
                
                return {
                    'is_temporal': True,
                    'temporal_type': temp_type,
                    'date_range': (start_date.isoformat(), end_date.isoformat())
                }
        
        return {
            'is_temporal': False,
            'temporal_type': None,
            'date_range': None
        }