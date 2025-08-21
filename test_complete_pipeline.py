"""
Test script for the complete Google Search + Gemini pipeline
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from google_search_client import GoogleSearchClient
from gemini_client import GeminiClient
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_complete_pipeline():
    """Test the complete research + question generation pipeline"""
    try:
        print("🔍 Testing Google Search Research...")
        
        # Test Google Search research
        search_client = GoogleSearchClient()
        research_result = search_client.research_company_patterns("Capgemini")
        
        print(f"✅ Research completed in {research_result['research_time']:.2f} seconds")
        print(f"📊 Found {research_result['source_count']} sources")
        print(f"📝 Content length: {len(research_result['research_content'])} characters")
        
        print("\n🤖 Testing Question Generation...")
        
        # Test question generation with research data
        gemini_client = GeminiClient()
        questions_result = gemini_client.generate_questions(
            research_result['research_content'],
            "Capgemini",
            5  # Generate 5 questions for testing
        )
        
        print(f"✅ Question generation completed in {questions_result['generation_time']:.2f} seconds")
        print(f"📋 Generated {questions_result['num_questions_generated']} questions")
        
        # Show sample questions
        sections = questions_result['questions']['sections']
        if sections and sections[0]['questions']:
            print(f"\n📝 Sample Questions from {sections[0]['section_name']}:")
            for i, question in enumerate(sections[0]['questions'][:2]):
                print(f"\nQ{i+1}: {question['question_text']}")
                for option in question['options']:
                    print(f"  {option}")
                print(f"  Answer: {question['correct_answer']}")
                print(f"  Difficulty: {question['difficulty']}")
        
        print(f"\n🎉 Complete pipeline test successful!")
        print(f"Total time: {research_result['research_time'] + questions_result['generation_time']:.2f} seconds")
        
    except Exception as e:
        print(f"❌ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_complete_pipeline()
