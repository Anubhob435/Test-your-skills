"""
Gemini Question Generation Service for UEM Placement Platform
Handles AI-powered question generation using Google Gemini 2.5-flash model
"""

import os
import json
import time
import logging
import requests
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GeminiAPIError(Exception):
    """Custom exception for Gemini API errors"""
    pass


class QuestionValidationError(Exception):
    """Custom exception for question validation errors"""
    pass


class GeminiClient:
    """
    Client for interacting with Google Gemini API for question generation
    Specialized for placement exam question creation
    """
    
    def __init__(self):
        """Initialize the Gemini client"""
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
        self.max_retries = 3
        self.retry_delay = 2
        self.timeout = 30
    
    def _create_question_generation_prompt(self, research_data: str, company: str, 
                                         num_questions: int = 20) -> str:
        """
        Create a structured prompt for question generation based on research data
        
        Args:
            research_data (str): Research content from Perplexity
            company (str): Company name
            num_questions (int): Number of questions to generate
            
        Returns:
            str: Formatted prompt for Gemini
        """
        prompt = f"""
        Based on the following research data about {company} placement exam patterns, generate {num_questions} practice questions that closely match their actual exam format.

        RESEARCH DATA:
        {research_data}

        INSTRUCTIONS:
        Generate questions in the following JSON format. Ensure the questions are realistic, varied in difficulty, and match the company's actual exam patterns based on the research data.

        Required JSON Structure:
        {{
            "company": "{company}",
            "year": 2025,
            "total_questions": {num_questions},
            "sections": [
                {{
                    "section_name": "Quantitative Aptitude",
                    "time_limit_minutes": 30,
                    "questions": [
                        {{
                            "id": 1,
                            "question_text": "Question text here",
                            "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
                            "correct_answer": "A",
                            "explanation": "Detailed explanation of the solution",
                            "difficulty": "medium",
                            "topic": "Specific topic name",
                            "time_estimate_seconds": 90
                        }}
                    ]
                }},
                {{
                    "section_name": "Logical Reasoning",
                    "time_limit_minutes": 25,
                    "questions": [...]
                }},
                {{
                    "section_name": "Verbal Ability",
                    "time_limit_minutes": 20,
                    "questions": [...]
                }}
            ]
        }}

        QUESTION GENERATION GUIDELINES:
        1. **Quantitative Aptitude**: Include arithmetic, algebra, geometry, data interpretation, number series, percentages, profit & loss, time & work, etc.
        2. **Logical Reasoning**: Include puzzles, seating arrangements, blood relations, coding-decoding, syllogisms, pattern recognition, etc.
        3. **Verbal Ability**: Include reading comprehension, grammar, vocabulary, sentence correction, para jumbles, etc.
        4. **Difficulty Distribution**: 30% easy, 50% medium, 20% hard
        5. **Answer Options**: Always provide exactly 4 options (A, B, C, D)
        6. **Explanations**: Provide clear, step-by-step explanations for each answer
        7. **Topics**: Use specific topic names that match the research data
        8. **Time Estimates**: Realistic time estimates for each question (60-180 seconds)

        IMPORTANT: 
        - Return ONLY valid JSON, no additional text or formatting
        - Ensure all questions are unique and non-repetitive
        - Match the difficulty and pattern mentioned in the research data
        - Include company-specific question types if mentioned in research
        - Distribute questions evenly across sections
        """
        
        return prompt.strip()
    
    def _make_generation_request(self, prompt: str) -> Dict[str, Any]:
        """
        Make a question generation request to Gemini API
        
        Args:
            prompt (str): Generation prompt
            
        Returns:
            Dict[str, Any]: API response
            
        Raises:
            GeminiAPIError: If API request fails
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
                "generationConfig": {
                    "temperature": 0.3,  # Lower temperature for more consistent output
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 8192,
                    "candidateCount": 1
                }
            }
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=request_body,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise GeminiAPIError(f"Gemini API request failed: {e}")
        except Exception as e:
            raise GeminiAPIError(f"Unexpected error in API request: {e}")
    
    def _extract_content_from_response(self, response: Dict[str, Any]) -> str:
        """
        Extract text content from Gemini API response
        
        Args:
            response (Dict[str, Any]): API response
            
        Returns:
            str: Extracted content
            
        Raises:
            GeminiAPIError: If content extraction fails
        """
        try:
            if 'candidates' not in response or not response['candidates']:
                raise GeminiAPIError("No candidates in API response")
            
            candidate = response['candidates'][0]
            
            if 'content' not in candidate or 'parts' not in candidate['content']:
                raise GeminiAPIError("Invalid response structure")
            
            parts = candidate['content']['parts']
            if not parts or 'text' not in parts[0]:
                raise GeminiAPIError("No text content in response")
            
            return parts[0]['text'].strip()
            
        except KeyError as e:
            raise GeminiAPIError(f"Missing key in response: {e}")
        except Exception as e:
            raise GeminiAPIError(f"Content extraction failed: {e}")
    
    def _validate_question_json(self, questions_json: Dict[str, Any]) -> bool:
        """
        Validate the structure and content of generated questions JSON
        
        Args:
            questions_json (Dict[str, Any]): Questions JSON to validate
            
        Returns:
            bool: True if valid
            
        Raises:
            QuestionValidationError: If validation fails
        """
        required_fields = ['company', 'year', 'total_questions', 'sections']
        
        # Check top-level fields
        for field in required_fields:
            if field not in questions_json:
                raise QuestionValidationError(f"Missing required field: {field}")
        
        # Validate sections
        sections = questions_json['sections']
        if not isinstance(sections, list) or len(sections) == 0:
            raise QuestionValidationError("Sections must be a non-empty list")
        
        for section in sections:
            # Check section fields
            section_fields = ['section_name', 'time_limit_minutes', 'questions']
            for field in section_fields:
                if field not in section:
                    raise QuestionValidationError(f"Missing section field: {field}")
            
            # Validate questions in section
            questions = section['questions']
            if not isinstance(questions, list) or len(questions) == 0:
                raise QuestionValidationError(f"Section {section['section_name']} has no questions")
            
            for i, question in enumerate(questions):
                # Check question fields
                question_fields = ['id', 'question_text', 'options', 'correct_answer', 'explanation', 'difficulty', 'topic']
                for field in question_fields:
                    if field not in question:
                        raise QuestionValidationError(f"Question {i+1} missing field: {field}")
                
                # Validate options
                options = question['options']
                if not isinstance(options, list) or len(options) != 4:
                    raise QuestionValidationError(f"Question {i+1} must have exactly 4 options")
                
                # Validate correct answer
                correct_answer = question['correct_answer']
                if correct_answer not in ['A', 'B', 'C', 'D']:
                    raise QuestionValidationError(f"Question {i+1} has invalid correct answer: {correct_answer}")
                
                # Validate difficulty
                difficulty = question['difficulty']
                if difficulty not in ['easy', 'medium', 'hard']:
                    raise QuestionValidationError(f"Question {i+1} has invalid difficulty: {difficulty}")
        
        return True
    
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
            GeminiAPIError: If all retries fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(f"API call failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries} attempts failed")
        
        raise GeminiAPIError(f"API call failed after {self.max_retries} attempts: {last_exception}")
    
    def generate_questions(self, research_data: str, company: str, 
                          num_questions: int = 20) -> Dict[str, Any]:
        """
        Generate placement exam questions based on research data
        
        Args:
            research_data (str): Research content from Perplexity
            company (str): Company name
            num_questions (int): Number of questions to generate
            
        Returns:
            Dict[str, Any]: Generated questions with metadata
            
        Raises:
            GeminiAPIError: If generation fails
            QuestionValidationError: If generated questions are invalid
        """
        logger.info(f"Starting question generation for {company} ({num_questions} questions)")
        
        try:
            # Create generation prompt
            prompt = self._create_question_generation_prompt(research_data, company, num_questions)
            logger.debug(f"Generated prompt length: {len(prompt)} characters")
            
            # Make API request with retry mechanism
            start_time = time.time()
            response = self._retry_api_call(self._make_generation_request, prompt)
            
            # Extract content
            content = self._extract_content_from_response(response)
            
            # Parse JSON
            try:
                # Clean content (remove markdown formatting if present)
                if content.startswith('```json'):
                    content = content.replace('```json', '').replace('```', '').strip()
                elif content.startswith('```'):
                    content = content.replace('```', '').strip()
                
                questions_json = json.loads(content)
            except json.JSONDecodeError as e:
                raise GeminiAPIError(f"Failed to parse JSON response: {e}")
            
            # Validate questions
            self._validate_question_json(questions_json)
            
            end_time = time.time()
            
            # Add metadata
            result = {
                'questions': questions_json,
                'generation_time': end_time - start_time,
                'timestamp': time.time(),
                'company': company,
                'num_questions_requested': num_questions,
                'num_questions_generated': questions_json.get('total_questions', 0),
                'success': True
            }
            
            logger.info(f"Question generation completed for {company} in {result['generation_time']:.2f} seconds")
            return result
            
        except Exception as e:
            logger.error(f"Question generation failed for {company}: {e}")
            raise GeminiAPIError(f"Failed to generate questions for {company}: {e}")
    
    def get_question_statistics(self, questions_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate statistics for generated questions
        
        Args:
            questions_data (Dict[str, Any]): Questions data
            
        Returns:
            Dict[str, Any]: Question statistics
        """
        try:
            sections = questions_data['questions']['sections']
            
            stats = {
                'total_sections': len(sections),
                'total_questions': 0,
                'difficulty_distribution': {'easy': 0, 'medium': 0, 'hard': 0},
                'section_breakdown': [],
                'topics_covered': set()
            }
            
            for section in sections:
                section_stats = {
                    'name': section['section_name'],
                    'question_count': len(section['questions']),
                    'time_limit': section['time_limit_minutes']
                }
                
                for question in section['questions']:
                    stats['total_questions'] += 1
                    difficulty = question.get('difficulty', 'medium')
                    stats['difficulty_distribution'][difficulty] += 1
                    
                    topic = question.get('topic', 'Unknown')
                    stats['topics_covered'].add(topic)
                
                stats['section_breakdown'].append(section_stats)
            
            # Convert set to list for JSON serialization
            stats['topics_covered'] = list(stats['topics_covered'])
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to calculate question statistics: {e}")
            return {}


# Example usage and testing
if __name__ == "__main__":
    try:
        # Initialize client
        client = GeminiClient()
        
        # Sample research data for testing
        sample_research = """
        TCS NQT 2025 Exam Pattern:
        - Duration: 90 minutes
        - Sections: Quantitative Aptitude (30 min), Logical Reasoning (25 min), Verbal Ability (20 min)
        - Question Types: Multiple choice questions
        - Difficulty: Medium level
        - Topics: Arithmetic, Algebra, Data Interpretation, Puzzles, Reading Comprehension
        """
        
        print("Testing Gemini question generation for TCS...")
        result = client.generate_questions(sample_research, "TCS NQT", 6)  # Small number for testing
        
        print(f"Generation completed successfully!")
        print(f"Company: {result['company']}")
        print(f"Generation time: {result['generation_time']:.2f} seconds")
        print(f"Questions requested: {result['num_questions_requested']}")
        print(f"Questions generated: {result['num_questions_generated']}")
        
        # Calculate statistics
        stats = client.get_question_statistics(result)
        print(f"\nQuestion Statistics:")
        print(f"Total sections: {stats['total_sections']}")
        print(f"Total questions: {stats['total_questions']}")
        print(f"Difficulty distribution: {stats['difficulty_distribution']}")
        
    except Exception as e:
        print(f"Error: {e}")