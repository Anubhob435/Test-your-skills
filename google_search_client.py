"""
Google Search Research Service for UEM Placement Platform
Uses Gemini 2.5 Flash with Google Search grounding for company research
"""

import os
import json
import time
import logging
import requests
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GoogleSearchAPIError(Exception):
    """Custom exception for Google Search API errors"""
    pass


class GoogleSearchClient:
    """
    Client for researching company placement patterns using Gemini 2.5 Flash with Google Search
    Replaces Perplexity functionality with Google's grounded search
    """
    
    def __init__(self):
        """Initialize the Google Search client"""
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY not found in environment variables")
        
        # API configuration
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
        self.headers = {
            'x-goog-api-key': self.api_key,
            'Content-Type': 'application/json'
        }
        
        # Generation parameters
        self.max_retries = int(os.getenv('GEMINI_MAX_RETRIES', 3))
        self.retry_delay = int(os.getenv('GEMINI_RETRY_DELAY', 2))
        self.timeout = int(os.getenv('GEMINI_TIMEOUT', 90))
    
    def _create_research_prompt(self, company: str) -> str:
        """
        Create a research prompt for company placement exam patterns
        
        Args:
            company (str): Company name
            
        Returns:
            str: Research prompt
        """
        return f"""
        Research the latest {company} placement exam pattern for 2024-2025 for freshers. 
        
        Please provide comprehensive information about:
        
        1. **Exam Structure and Format:**
           - Total number of questions
           - Time limit for the exam
           - Section-wise breakdown (Quantitative, Logical, Verbal, Technical, etc.)
           - Question distribution across sections
           - Difficulty level and pattern
        
        2. **Question Types by Section:**
           - Quantitative Aptitude: Specific topics covered (arithmetic, algebra, geometry, data interpretation, etc.)
           - Logical Reasoning: Types of puzzles, patterns, arrangements, coding-decoding, etc.
           - Verbal Ability: Grammar, vocabulary, reading comprehension, sentence correction, etc.
           - Technical Questions: Programming concepts, data structures, algorithms, etc.
        
        3. **Recent Changes and Trends:**
           - Any updates in the exam pattern for 2024-2025
           - Emerging question types or topics
           - Difficulty level changes
        
        4. **Important Topics and Weightage:**
           - Most frequently asked question types
           - High-priority topics for each section
           - Topics with maximum marks allocation
        
        5. **Preparation Tips and Insights:**
           - Recommended preparation strategies
           - Time management tips
           - Common mistakes to avoid
        
        Please provide accurate, up-to-date information with specific examples where possible.
        Focus on creating a comprehensive guide that can be used to generate realistic practice questions.
        """
    
    def _make_research_request(self, prompt: str) -> Dict[str, Any]:
        """
        Make a research request to Gemini API with Google Search
        
        Args:
            prompt (str): Research prompt
            
        Returns:
            Dict[str, Any]: API response
            
        Raises:
            GoogleSearchAPIError: If API request fails
        """
        try:
            request_body = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt}
                        ]
                    }
                ],
                "tools": [
                    {
                        "google_search": {}
                    }
                ],
                "generationConfig": {
                    "temperature": 0.3,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 8192,
                    "candidateCount": 1
                }
            }
            
            logger.info(f"Making Google Search research request with timeout: {self.timeout}s")
            start_time = time.time()
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=request_body,
                timeout=self.timeout
            )
            
            end_time = time.time()
            logger.info(f"Research request completed in {end_time - start_time:.2f} seconds")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout as e:
            logger.error(f"Research request timed out after {self.timeout} seconds: {e}")
            raise GoogleSearchAPIError(f"Google Search request timed out after {self.timeout}s: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Research request failed: {e}")
            raise GoogleSearchAPIError(f"Google Search request failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in research request: {e}")
            raise GoogleSearchAPIError(f"Unexpected error in research request: {e}")
    
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
            GoogleSearchAPIError: If all retries fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except requests.exceptions.Timeout as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (3 ** attempt)
                    logger.warning(f"Research timeout (attempt {attempt + 1}/{self.max_retries}): {e}")
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries} attempts failed due to timeouts")
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Research call failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries} attempts failed")
        
        raise GoogleSearchAPIError(f"Research call failed after {self.max_retries} attempts: {last_exception}")
    
    def _extract_research_content(self, response: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Extract research content and sources from Google Search response
        
        Args:
            response (Dict[str, Any]): API response
            
        Returns:
            Tuple[str, List[Dict[str, Any]]]: Research content and sources
            
        Raises:
            GoogleSearchAPIError: If content extraction fails
        """
        try:
            if 'candidates' not in response or not response['candidates']:
                raise GoogleSearchAPIError("No candidates in research response")
            
            candidate = response['candidates'][0]
            
            if 'content' not in candidate or 'parts' not in candidate['content']:
                raise GoogleSearchAPIError("Invalid response structure")
            
            parts = candidate['content']['parts']
            if not parts or 'text' not in parts[0]:
                raise GoogleSearchAPIError("No text content in response")
            
            content = parts[0]['text'].strip()
            
            # Extract sources from grounding metadata
            sources = []
            if 'groundingMetadata' in candidate:
                grounding_chunks = candidate['groundingMetadata'].get('groundingChunks', [])
                for chunk in grounding_chunks:
                    if 'web' in chunk:
                        web_info = chunk['web']
                        sources.append({
                            'title': web_info.get('title', 'Unknown'),
                            'uri': web_info.get('uri', ''),
                        })
            
            return content, sources
            
        except KeyError as e:
            raise GoogleSearchAPIError(f"Missing key in response: {e}")
        except Exception as e:
            raise GoogleSearchAPIError(f"Content extraction failed: {e}")
    
    def research_company_patterns(self, company: str) -> Dict[str, Any]:
        """
        Research placement exam patterns for a specific company
        
        Args:
            company (str): Company name
            
        Returns:
            Dict[str, Any]: Research results with metadata
            
        Raises:
            GoogleSearchAPIError: If research fails
        """
        logger.info(f"Starting placement pattern research for {company}")
        
        try:
            # Create research prompt
            prompt = self._create_research_prompt(company)
            logger.debug(f"Generated research prompt length: {len(prompt)} characters")
            
            # Make API request with retry mechanism
            start_time = time.time()
            response = self._retry_api_call(self._make_research_request, prompt)
            
            # Extract content and sources
            content, sources = self._extract_research_content(response)
            
            end_time = time.time()
            
            # Prepare result
            result = {
                'company': company,
                'research_content': content,
                'sources': sources,
                'research_time': end_time - start_time,
                'timestamp': time.time(),
                'source_count': len(sources),
                'success': True
            }
            
            logger.info(f"Research completed for {company} in {result['research_time']:.2f} seconds")
            logger.info(f"Found {len(sources)} sources")
            
            return result
            
        except Exception as e:
            logger.error(f"Research failed for {company}: {e}")
            raise GoogleSearchAPIError(f"Failed to research {company} patterns: {e}")
    
    def validate_company_name(self, company: str) -> bool:
        """
        Validate if company name is acceptable for research
        
        Args:
            company (str): Company name to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not company or not isinstance(company, str):
            return False
        
        # Clean and validate company name
        company = company.strip()
        if len(company) < 2 or len(company) > 100:
            return False
        
        # Check for valid characters (letters, numbers, spaces, common punctuation)
        import re
        if not re.match(r'^[a-zA-Z0-9\s\-&\.]+$', company):
            return False
        
        return True
    
    def get_supported_companies(self) -> List[str]:
        """
        Get list of companies that can be researched
        
        Returns:
            List[str]: List of supported company names
        """
        return [
            "TCS", "Infosys", "Wipro", "Capgemini", "Accenture", "Cognizant",
            "HCL Technologies", "Tech Mahindra", "IBM", "Microsoft", "Amazon",
            "Google", "Adobe", "Oracle", "Salesforce", "SAP", "Deloitte",
            "EY", "PwC", "KPMG", "Flipkart", "Paytm", "Zomato", "Swiggy",
            "Ola", "Uber", "Samsung", "LG", "Siemens", "Bosch", "L&T",
            "Bajaj", "Maruti", "HDFC", "ICICI", "SBI", "Axis Bank"
        ]


# Test function
def test_google_search_research():
    """Test Google Search research functionality"""
    try:
        client = GoogleSearchClient()
        result = client.research_company_patterns("TCS")
        
        print(f"Research successful for {result['company']}")
        print(f"Research time: {result['research_time']:.2f} seconds")
        print(f"Sources found: {result['source_count']}")
        print(f"Content length: {len(result['research_content'])} characters")
        print("\nFirst 500 characters of research:")
        print(result['research_content'][:500])
        
        if result['sources']:
            print(f"\nSample sources:")
            for i, source in enumerate(result['sources'][:3]):
                print(f"{i+1}. {source['title']}: {source['uri']}")
        
    except Exception as e:
        print(f"Test failed: {e}")


if __name__ == "__main__":
    test_google_search_research()
