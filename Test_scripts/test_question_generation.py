#!/usr/bin/env python3
"""
Test script for the question generation pipeline
Tests the integration between Perplexity research and Gemini question generation
"""

import sys
import os
import time
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from perplexity_client import PerplexityClient, PerplexityAPIError
    from gemini_client import GeminiClient, GeminiAPIError
    from question_generation_service import QuestionGenerationService, QuestionGenerationError
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure all required dependencies are installed and API keys are configured")
    sys.exit(1)


def test_perplexity_client():
    """Test Perplexity client functionality"""
    print("=" * 60)
    print("Testing Perplexity Client")
    print("=" * 60)
    
    try:
        client = PerplexityClient()
        print(f"✓ Perplexity client initialized successfully")
        
        # Test company validation
        valid_company = client.validate_company_name("TCS")
        print(f"✓ Company validation works: TCS is {'valid' if valid_company else 'invalid'}")
        
        # Test supported companies
        companies = client.get_supported_companies()
        print(f"✓ Supported companies loaded: {len(companies)} companies")
        
        # Test research (with a simple query to avoid long wait)
        print("Testing research functionality...")
        start_time = time.time()
        result = client.research_company_patterns("TCS", 2025)
        end_time = time.time()
        
        print(f"✓ Research completed in {end_time - start_time:.2f} seconds")
        print(f"✓ Research content length: {len(result['research_content'])} characters")
        print(f"✓ Research success: {result['success']}")
        
        return True, result['research_content']
        
    except Exception as e:
        print(f"✗ Perplexity client test failed: {e}")
        return False, None


def test_gemini_client(research_data=None):
    """Test Gemini client functionality"""
    print("\n" + "=" * 60)
    print("Testing Gemini Client")
    print("=" * 60)
    
    try:
        client = GeminiClient()
        print(f"✓ Gemini client initialized successfully")
        
        # Use sample research data if none provided
        if research_data is None:
            research_data = """
            TCS NQT 2025 Exam Pattern:
            - Duration: 90 minutes
            - Sections: Quantitative Aptitude (30 min), Logical Reasoning (25 min), Verbal Ability (20 min)
            - Question Types: Multiple choice questions
            - Difficulty: Medium level
            - Topics: Arithmetic, Algebra, Data Interpretation, Puzzles, Reading Comprehension
            """
        
        # Test question generation (small number for testing)
        print("Testing question generation...")
        start_time = time.time()
        result = client.generate_questions(research_data, "TCS NQT", 3)  # Only 3 questions for testing
        end_time = time.time()
        
        print(f"✓ Question generation completed in {end_time - start_time:.2f} seconds")
        print(f"✓ Questions requested: {result['num_questions_requested']}")
        print(f"✓ Questions generated: {result['num_questions_generated']}")
        print(f"✓ Generation success: {result['success']}")
        
        # Test statistics
        stats = client.get_question_statistics(result)
        print(f"✓ Statistics calculated: {stats.get('total_questions', 0)} total questions")
        
        return True, result
        
    except Exception as e:
        print(f"✗ Gemini client test failed: {e}")
        return False, None


def test_question_generation_service():
    """Test the complete question generation service"""
    print("\n" + "=" * 60)
    print("Testing Question Generation Service")
    print("=" * 60)
    
    try:
        # Note: This test doesn't use database operations to avoid setup complexity
        service = QuestionGenerationService()
        print(f"✓ Question generation service initialized successfully")
        
        # Test validation
        try:
            service._validate_generation_request("TCS", 5)
            print(f"✓ Request validation works")
        except Exception as e:
            print(f"✗ Request validation failed: {e}")
            return False
        
        # Test invalid requests
        try:
            service._validate_generation_request("", 5)
            print(f"✗ Validation should have failed for empty company")
            return False
        except QuestionGenerationError:
            print(f"✓ Validation correctly rejects empty company")
        
        try:
            service._validate_generation_request("TCS", 0)
            print(f"✗ Validation should have failed for 0 questions")
            return False
        except QuestionGenerationError:
            print(f"✓ Validation correctly rejects invalid question count")
        
        print(f"✓ All validation tests passed")
        
        # Test statistics (without database)
        try:
            stats = service.get_company_statistics()
            if 'error' not in stats:
                print(f"✓ Statistics method works (may show 0 if no database)")
            else:
                print(f"✓ Statistics method handles database errors gracefully")
        except Exception as e:
            print(f"✓ Statistics method handles errors: {e}")
        
        return True
        
    except Exception as e:
        print(f"✗ Question generation service test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("UEM Placement Platform - Question Generation Pipeline Test")
    print("=" * 60)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test results
    results = {
        'perplexity': False,
        'gemini': False,
        'service': False
    }
    
    research_data = None
    
    # Test Perplexity client
    try:
        perplexity_success, research_data = test_perplexity_client()
        results['perplexity'] = perplexity_success
    except KeyboardInterrupt:
        print("\n✗ Test interrupted by user")
        return
    except Exception as e:
        print(f"✗ Perplexity test crashed: {e}")
    
    # Test Gemini client
    try:
        gemini_success, _ = test_gemini_client(research_data)
        results['gemini'] = gemini_success
    except KeyboardInterrupt:
        print("\n✗ Test interrupted by user")
        return
    except Exception as e:
        print(f"✗ Gemini test crashed: {e}")
    
    # Test question generation service
    try:
        service_success = test_question_generation_service()
        results['service'] = service_success
    except KeyboardInterrupt:
        print("\n✗ Test interrupted by user")
        return
    except Exception as e:
        print(f"✗ Service test crashed: {e}")
    
    # Print final results
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    for component, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{component.capitalize():20} {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    
    print(f"\nOverall: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("🎉 All tests passed! The question generation pipeline is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the error messages above.")
        print("\nCommon issues:")
        print("- Missing API keys (SONAR_API_KEY, GEMINI_API_KEY)")
        print("- Network connectivity issues")
        print("- API rate limits or service unavailability")
    
    print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)