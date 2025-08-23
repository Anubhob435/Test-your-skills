"""
Question Generation Service for UEM Placement Platform
Orchestrates the complete pipeline from research to question generation and storage
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError

from google_search_client import GoogleSearchClient, GoogleSearchAPIError
from gemini_client import GeminiClient, GeminiAPIError, QuestionValidationError
from models import db, Test, Question

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QuestionGenerationError(Exception):
    """Custom exception for question generation pipeline errors"""
    pass


class QuestionGenerationService:
    """
    Service that orchestrates the complete question generation pipeline
    Combines Google Search research with Gemini question generation
    """
    
    def __init__(self):
        """Initialize the question generation service"""
        self.search_client = GoogleSearchClient()
        self.gemini_client = GeminiClient()
        
        # Configuration
        self.cache_duration_hours = 24  # Cache research for 24 hours
        self.default_questions_per_test = 20
        self.max_concurrent_operations = 3
    
    def _check_existing_test(self, company: str, year: int = 2025) -> Optional[Test]:
        """
        Check if a recent test exists for the company
        
        Args:
            company (str): Company name
            year (int): Test year
            
        Returns:
            Optional[Test]: Existing test if found and recent, None otherwise
        """
        try:
            # Look for tests created in the last 24 hours
            cutoff_time = datetime.utcnow() - timedelta(hours=self.cache_duration_hours)
            
            existing_test = Test.query.filter(
                Test.company.ilike(f'%{company}%'),
                Test.year == year,
                Test.created_at >= cutoff_time
            ).first()
            
            if existing_test:
                # Check if test has questions
                question_count = Question.query.filter_by(test_id=existing_test.id).count()
                if question_count > 0:
                    logger.info(f"Found existing test for {company} with {question_count} questions")
                    return existing_test
            
            return None
            
        except SQLAlchemyError as e:
            logger.error(f"Database error checking existing test: {e}")
            return None
    
    def _save_test_to_database(self, questions_data: Dict[str, Any], 
                              research_data: str, company: str, year: int = 2025) -> Test:
        """
        Save generated questions to database
        
        Args:
            questions_data (Dict[str, Any]): Generated questions data
            research_data (str): Research content used
            company (str): Company name
            year (int): Test year
            
        Returns:
            Test: Saved test object
            
        Raises:
            QuestionGenerationError: If database save fails
        """
        try:
            # Create test record
            test = Test(
                company=company,
                year=year,
                pattern_data=research_data[:5000]  # Truncate if too long
            )
            
            db.session.add(test)
            db.session.flush()  # Get test ID
            
            # Save questions
            questions_saved = 0
            sections = questions_data.get('sections', [])
            
            for section in sections:
                section_name = section.get('section_name', 'Unknown')
                section_questions = section.get('questions', [])
                
                for q_data in section_questions:
                    question = Question(
                        test_id=test.id,
                        section=section_name,
                        question_text=q_data.get('question_text', ''),
                        options=q_data.get('options', []),
                        correct_answer=q_data.get('correct_answer', 'A'),
                        explanation=q_data.get('explanation', ''),
                        difficulty=q_data.get('difficulty', 'medium')
                    )
                    
                    db.session.add(question)
                    questions_saved += 1
            
            db.session.commit()
            
            logger.info(f"Saved test for {company} with {questions_saved} questions (Test ID: {test.id})")
            return test
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error saving test: {e}")
            raise QuestionGenerationError(f"Failed to save test to database: {e}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error saving test: {e}")
            raise QuestionGenerationError(f"Unexpected error saving test: {e}")
    
    def _validate_generation_request(self, company: str, num_questions: int) -> bool:
        """
        Validate question generation request parameters
        
        Args:
            company (str): Company name
            num_questions (int): Number of questions requested
            
        Returns:
            bool: True if valid
            
        Raises:
            QuestionGenerationError: If validation fails
        """
        if not company or not company.strip():
            raise QuestionGenerationError("Company name cannot be empty")
        
        if not isinstance(num_questions, int) or num_questions < 1 or num_questions > 100:
            raise QuestionGenerationError("Number of questions must be between 1 and 100")
        
        # Validate company name
        if not self.search_client.validate_company_name(company):
            logger.warning(f"Company '{company}' not in supported list, proceeding anyway")
        
        return True
    
    async def _async_research_company(self, company: str, year: int) -> Dict[str, Any]:
        """
        Async wrapper for company research
        
        Args:
            company (str): Company name
            year (int): Target year
            
        Returns:
            Dict[str, Any]: Research results
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.search_client.research_company_patterns, 
            company
        )
    
    async def _async_generate_questions(self, research_data: str, company: str, 
                                      num_questions: int) -> Dict[str, Any]:
        """
        Async wrapper for question generation
        
        Args:
            research_data (str): Research content
            company (str): Company name
            num_questions (int): Number of questions
            
        Returns:
            Dict[str, Any]: Generated questions
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.gemini_client.generate_questions,
            research_data,
            company,
            num_questions
        )
    
    async def _async_generate_questions_chunked(self, research_data: str, company: str, 
                                              num_questions: int) -> Dict[str, Any]:
        """
        Async wrapper for chunked question generation
        
        Args:
            research_data (str): Research content
            company (str): Company name
            num_questions (int): Number of questions
            
        Returns:
            Dict[str, Any]: Generated questions
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.gemini_client.generate_questions_chunked,
            research_data,
            company,
            num_questions,
            8  # 8 questions per chunk for better reliability
        )
    
    async def generate_test_async(self, company: str, num_questions: int = None, 
                                year: int = 2025, force_regenerate: bool = False) -> Dict[str, Any]:
        """
        Asynchronously generate a complete test for a company
        
        Args:
            company (str): Company name
            num_questions (int): Number of questions to generate
            year (int): Target year
            force_regenerate (bool): Force regeneration even if recent test exists
            
        Returns:
            Dict[str, Any]: Complete test generation result
            
        Raises:
            QuestionGenerationError: If generation fails
        """
        if num_questions is None:
            num_questions = self.default_questions_per_test
        
        logger.info(f"Starting async test generation for {company} ({num_questions} questions)")
        
        try:
            # Validate request
            self._validate_generation_request(company, num_questions)
            
            # Check for existing test
            if not force_regenerate:
                existing_test = self._check_existing_test(company, year)
                if existing_test:
                    questions = Question.query.filter_by(test_id=existing_test.id).all()
                    return {
                        'test_id': existing_test.id,
                        'company': company,
                        'year': year,
                        'num_questions': len(questions),
                        'created_at': existing_test.created_at.isoformat(),
                        'from_cache': True,
                        'success': True
                    }
            
            start_time = time.time()
            
            # Step 1: Research company patterns (async)
            logger.info(f"Step 1: Researching {company} placement patterns...")
            research_result = await self._async_research_company(company, year)
            research_data = research_result['research_content']
            
            # Step 2: Generate questions based on research (async)
            logger.info(f"Step 2: Generating {num_questions} questions for {company}...")
            
            # Use chunked generation for large requests to avoid timeouts
            if num_questions > 15:
                generation_result = await self._async_generate_questions_chunked(
                    research_data, company, num_questions
                )
            else:
                generation_result = await self._async_generate_questions(
                    research_data, company, num_questions
                )
            questions_data = generation_result['questions']
            
            # Step 3: Validate and save to database
            logger.info(f"Step 3: Saving test to database...")
            test = self._save_test_to_database(questions_data, research_data, company, year)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Prepare result
            result = {
                'test_id': test.id,
                'company': company,
                'year': year,
                'num_questions': generation_result['num_questions_generated'],
                'created_at': test.created_at.isoformat(),
                'generation_time': total_time,
                'research_time': research_result.get('research_time', 0),  # Fixed field name
                'question_generation_time': generation_result['generation_time'],
                'from_cache': False,
                'success': True,
                'sections': [section['section_name'] for section in questions_data.get('sections', [])]
            }
            
            logger.info(f"Test generation completed for {company} in {total_time:.2f} seconds")
            return result
            
        except (GoogleSearchAPIError, GeminiAPIError, QuestionValidationError) as e:
            logger.error(f"API error during test generation: {e}")
            raise QuestionGenerationError(f"API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during test generation: {e}")
            raise QuestionGenerationError(f"Test generation failed: {e}")
    
    def generate_test_sync(self, company: str, num_questions: int = None, 
                          year: int = 2025, force_regenerate: bool = False) -> Dict[str, Any]:
        """
        Synchronously generate a complete test for a company
        
        Args:
            company (str): Company name
            num_questions (int): Number of questions to generate
            year (int): Target year
            force_regenerate (bool): Force regeneration even if recent test exists
            
        Returns:
            Dict[str, Any]: Complete test generation result
        """
        try:
            # Run async function in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self.generate_test_async(company, num_questions, year, force_regenerate)
                )
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"Sync test generation failed: {e}")
            raise QuestionGenerationError(f"Test generation failed: {e}")
    
    async def generate_multiple_tests_async(self, companies: List[str], 
                                          num_questions: int = None, 
                                          year: int = 2025) -> Dict[str, Any]:
        """
        Generate tests for multiple companies concurrently
        
        Args:
            companies (List[str]): List of company names
            num_questions (int): Number of questions per test
            year (int): Target year
            
        Returns:
            Dict[str, Any]: Results for all companies
        """
        if num_questions is None:
            num_questions = self.default_questions_per_test
        
        logger.info(f"Starting batch test generation for {len(companies)} companies")
        
        # Create semaphore to limit concurrent operations
        semaphore = asyncio.Semaphore(self.max_concurrent_operations)
        
        async def generate_with_semaphore(company: str) -> Tuple[str, Dict[str, Any]]:
            async with semaphore:
                try:
                    result = await self.generate_test_async(company, num_questions, year)
                    return company, result
                except Exception as e:
                    logger.error(f"Failed to generate test for {company}: {e}")
                    return company, {
                        'success': False,
                        'error': str(e),
                        'company': company
                    }
        
        # Execute all generations concurrently
        tasks = [generate_with_semaphore(company) for company in companies]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful = 0
        failed = 0
        company_results = {}
        
        for company, result in results:
            if isinstance(result, Exception):
                company_results[company] = {
                    'success': False,
                    'error': str(result),
                    'company': company
                }
                failed += 1
            else:
                company_results[company] = result
                if result.get('success', False):
                    successful += 1
                else:
                    failed += 1
        
        return {
            'total_companies': len(companies),
            'successful': successful,
            'failed': failed,
            'results': company_results,
            'success': successful > 0
        }
    
    def get_test_by_id(self, test_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a test by ID with all questions
        
        Args:
            test_id (int): Test ID
            
        Returns:
            Optional[Dict[str, Any]]: Test data with questions
        """
        try:
            test = Test.query.get(test_id)
            if not test:
                return None
            
            questions = Question.query.filter_by(test_id=test_id).all()
            
            # Group questions by section
            sections = {}
            for question in questions:
                section_name = question.section
                if section_name not in sections:
                    sections[section_name] = []
                
                sections[section_name].append({
                    'id': question.id,
                    'question_text': question.question_text,
                    'options': question.options,
                    'correct_answer': question.correct_answer,
                    'explanation': question.explanation,
                    'difficulty': question.difficulty
                })
            
            return {
                'test_id': test.id,
                'company': test.company,
                'year': test.year,
                'created_at': test.created_at.isoformat(),
                'total_questions': len(questions),
                'sections': sections
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving test {test_id}: {e}")
            return None
    
    def get_company_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about generated tests
        
        Returns:
            Dict[str, Any]: Test statistics
        """
        try:
            # Get test counts by company
            company_stats = db.session.query(
                Test.company,
                db.func.count(Test.id).label('test_count'),
                db.func.max(Test.created_at).label('latest_test')
            ).group_by(Test.company).all()
            
            # Get total question count
            total_questions = db.session.query(db.func.count(Question.id)).scalar()
            
            # Get total tests
            total_tests = db.session.query(db.func.count(Test.id)).scalar()
            
            return {
                'total_tests': total_tests,
                'total_questions': total_questions,
                'companies': [
                    {
                        'company': stat.company,
                        'test_count': stat.test_count,
                        'latest_test': stat.latest_test.isoformat() if stat.latest_test else None
                    }
                    for stat in company_stats
                ],
                'supported_companies': self.search_client.get_supported_companies()
            }
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting statistics: {e}")
            return {'error': str(e)}


# Example usage and testing
if __name__ == "__main__":
    try:
        # Initialize service
        service = QuestionGenerationService()
        
        print("Testing question generation service...")
        
        # Test single company generation
        result = service.generate_test_sync("TCS NQT", 6)  # Small number for testing
        
        print(f"Test generation completed!")
        print(f"Test ID: {result['test_id']}")
        print(f"Company: {result['company']}")
        print(f"Questions: {result['num_questions']}")
        print(f"Generation time: {result.get('generation_time', 0):.2f} seconds")
        print(f"From cache: {result['from_cache']}")
        
        # Test retrieval
        test_data = service.get_test_by_id(result['test_id'])
        if test_data:
            print(f"\nRetrieved test data:")
            print(f"Sections: {list(test_data['sections'].keys())}")
            for section, questions in test_data['sections'].items():
                print(f"  {section}: {len(questions)} questions")
        
    except Exception as e:
        print(f"Error: {e}")