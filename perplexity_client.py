"""
Perplexity AI Research Service for UEM Placement Platform
Handles company-specific placement research using Perplexity's sonar-deep-research model
"""

import os
import time
import logging
from typing import Optional, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PerplexityAPIError(Exception):
    """Custom exception for Perplexity API errors"""
    pass


class PerplexityClient:
    """
    Client for interacting with Perplexity AI's sonar-deep-research model
    Specialized for placement exam pattern research
    """
    
    def __init__(self):
        """Initialize the Perplexity client"""
        self.api_key = os.getenv("SONAR_API_KEY")
        if not self.api_key:
            raise RuntimeError("SONAR_API_KEY not found in environment variables")
        
        # Initialize OpenAI client for Perplexity
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.perplexity.ai"
        )
        
        # Configuration
        self.model = "sonar-deep-research"
        self.max_tokens = 2048
        self.temperature = 0.1  # Lower temperature for factual research
        self.max_retries = 3
        self.retry_delay = 2  # seconds
    
    def _generate_company_research_query(self, company: str, year: int = 2025) -> str:
        """
        Generate a comprehensive research query for company placement patterns
        
        Args:
            company (str): Company name (e.g., "TCS", "Infosys", "Capgemini")
            year (int): Target year for placement patterns
            
        Returns:
            str: Formatted research query
        """
        query = f"""
        Conduct comprehensive research on {company} placement exam patterns and recruitment process for {year}. 
        
        Please provide detailed information on:
        
        1. **Exam Structure & Format:**
           - Number of sections and their names
           - Time allocation for each section
           - Total duration of the exam
           - Question types (MCQ, coding, descriptive)
           
        2. **Subject Areas & Topics:**
           - Quantitative Aptitude topics and difficulty level
           - Logical Reasoning patterns and question types
           - Verbal Ability sections and focus areas
           - Technical/Programming questions if applicable
           - Company-specific sections or unique patterns
           
        3. **Difficulty Analysis:**
           - Overall difficulty level (Easy/Medium/Hard)
           - Section-wise difficulty distribution
           - Cut-off scores and selection criteria
           - Negative marking scheme if any
           
        4. **Recent Changes & Trends:**
           - Any updates to exam pattern in {year-1} or {year}
           - New question types or sections introduced
           - Changes in difficulty level or time allocation
           - Online vs offline exam format
           
        5. **Preparation Strategy:**
           - Key focus areas for maximum score
           - Common mistake patterns to avoid
           - Time management strategies
           - Recommended practice question types
           
        Focus on the most recent and accurate information available for {company} recruitment process.
        """
        
        return query.strip()
    
    def _retry_api_call(self, func, *args, **kwargs) -> Any:
        """
        Retry mechanism for API calls with exponential backoff
        
        Args:
            func: Function to retry
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            PerplexityAPIError: If all retries fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"API call failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries} attempts failed")
        
        raise PerplexityAPIError(f"API call failed after {self.max_retries} attempts: {last_exception}")
    
    def _make_research_request(self, query: str) -> str:
        """
        Make a research request to Perplexity API
        
        Args:
            query (str): Research query
            
        Returns:
            str: Research response content
            
        Raises:
            PerplexityAPIError: If API request fails
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": query}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=False
            )
            
            if not response.choices or not response.choices[0].message:
                raise PerplexityAPIError("Empty response from Perplexity API")
            
            content = response.choices[0].message.content
            if not content:
                raise PerplexityAPIError("No content in API response")
            
            return content.strip()
            
        except Exception as e:
            raise PerplexityAPIError(f"Perplexity API request failed: {e}")
    
    def research_company_patterns(self, company: str, year: int = 2025) -> Dict[str, Any]:
        """
        Research placement exam patterns for a specific company
        
        Args:
            company (str): Company name
            year (int): Target year for research
            
        Returns:
            Dict[str, Any]: Research results with metadata
            
        Raises:
            PerplexityAPIError: If research fails
        """
        logger.info(f"Starting research for {company} placement patterns ({year})")
        
        try:
            # Generate research query
            query = self._generate_company_research_query(company, year)
            logger.debug(f"Generated query: {query[:100]}...")
            
            # Make API request with retry mechanism
            start_time = time.time()
            content = self._retry_api_call(self._make_research_request, query)
            end_time = time.time()
            
            # Prepare result
            result = {
                'company': company,
                'year': year,
                'research_content': content,
                'query_used': query,
                'timestamp': time.time(),
                'response_time': end_time - start_time,
                'success': True
            }
            
            logger.info(f"Research completed for {company} in {result['response_time']:.2f} seconds")
            return result
            
        except Exception as e:
            logger.error(f"Research failed for {company}: {e}")
            raise PerplexityAPIError(f"Failed to research {company} patterns: {e}")
    
    def get_supported_companies(self) -> list:
        """
        Get list of companies supported for research
        
        Returns:
            list: List of supported company names
        """
        return [
            "TCS", "TCS NQT", "Tata Consultancy Services",
            "Infosys", "Infosys Springboard",
            "Capgemini", "Capgemini 2025",
            "Wipro", "Wipro WILP",
            "Accenture", "Accenture Digital",
            "Cognizant", "CTS",
            "HCL Technologies", "HCL",
            "Tech Mahindra",
            "IBM", "IBM India",
            "Microsoft", "Microsoft India",
            "Amazon", "Amazon India",
            "Google", "Google India",
            "Deloitte", "Deloitte USI",
            "EY", "Ernst & Young",
            "PwC", "PricewaterhouseCoopers",
            "KPMG"
        ]
    
    def validate_company_name(self, company: str) -> bool:
        """
        Validate if company name is supported
        
        Args:
            company (str): Company name to validate
            
        Returns:
            bool: True if supported, False otherwise
        """
        supported = self.get_supported_companies()
        return any(company.lower() in supported_company.lower() 
                  for supported_company in supported)


# Example usage and testing
if __name__ == "__main__":
    try:
        # Initialize client
        client = PerplexityClient()
        
        # Test research for TCS
        print("Testing Perplexity research for TCS...")
        result = client.research_company_patterns("TCS NQT", 2025)
        
        print(f"Research completed successfully!")
        print(f"Company: {result['company']}")
        print(f"Response time: {result['response_time']:.2f} seconds")
        print(f"Content length: {len(result['research_content'])} characters")
        print("\nFirst 500 characters of research:")
        print(result['research_content'][:500] + "...")
        
    except Exception as e:
        print(f"Error: {e}")