# AI Services Integration - UEM Placement Platform

This document explains the AI services integration implemented for the UEM Placement Platform.

## Overview

The platform integrates two AI services to create dynamic, company-specific placement test questions:

1. **Perplexity AI** - For researching latest placement exam patterns
2. **Google Gemini** - For generating practice questions based on research

## Components

### 1. PerplexityClient (`perplexity_client.py`)

Handles company-specific placement research using Perplexity's sonar-deep-research model.

**Key Features:**
- Company-specific research query generation
- Retry mechanism with exponential backoff
- Support for 31+ major placement companies
- Comprehensive error handling

**Usage:**
```python
from perplexity_client import PerplexityClient

client = PerplexityClient()
result = client.research_company_patterns("TCS NQT", 2025)
print(result['research_content'])
```

### 2. GeminiClient (`gemini_client.py`)

Generates placement exam questions using Google Gemini 2.5-flash model.

**Key Features:**
- Structured prompt generation for question creation
- JSON response validation and parsing
- Support for multiple question types (MCQ, aptitude, reasoning)
- Question statistics and validation

**Usage:**
```python
from gemini_client import GeminiClient

client = GeminiClient()
questions = client.generate_questions(research_data, "TCS NQT", 20)
print(f"Generated {questions['num_questions_generated']} questions")
```

### 3. QuestionGenerationService (`question_generation_service.py`)

Orchestrates the complete pipeline from research to question generation and storage.

**Key Features:**
- Async question generation workflow
- Database integration for storing tests and questions
- Caching mechanism (24-hour cache for recent tests)
- Batch generation for multiple companies
- Comprehensive error handling and logging

**Usage:**
```python
from question_generation_service import QuestionGenerationService

service = QuestionGenerationService()

# Generate test synchronously
result = service.generate_test_sync("TCS NQT", 20)
print(f"Test ID: {result['test_id']}")

# Generate test asynchronously
import asyncio
result = asyncio.run(service.generate_test_async("Infosys", 15))
```

## Configuration

### Environment Variables

Make sure these are set in your `.env` file:

```env
SONAR_API_KEY=your_perplexity_api_key
GEMINI_API_KEY=your_gemini_api_key
```

### Database Models

The service integrates with existing database models:
- `Test` - Stores test metadata
- `Question` - Stores individual questions with options and explanations

## API Integration Points

The AI services are designed to integrate with the Flask application through these endpoints:

- `POST /api/tests/generate/{company}` - Generate new test for company
- `GET /api/tests/{test_id}` - Retrieve generated test
- `GET /api/companies` - List supported companies

## Testing

Run the test suite to verify integration:

```bash
python test_question_generation.py
```

This tests:
- Perplexity API connectivity and research functionality
- Gemini API connectivity and question generation
- Service orchestration and validation

## Supported Companies

The system supports 31+ major placement companies including:
- TCS, TCS NQT
- Infosys, Infosys Springboard  
- Capgemini, Wipro, Accenture
- Cognizant, HCL Technologies
- Microsoft, Amazon, Google
- Deloitte, EY, PwC, KPMG
- And more...

## Error Handling

The system includes comprehensive error handling:

- **API Errors**: Retry mechanism with exponential backoff
- **Validation Errors**: JSON structure and content validation
- **Database Errors**: Transaction rollback and error logging
- **Network Errors**: Timeout handling and graceful degradation

## Performance

- **Research Time**: ~2-3 minutes per company (cached for 24 hours)
- **Question Generation**: ~15-30 seconds for 20 questions
- **Total Pipeline**: ~3-4 minutes for new company, <1 second for cached
- **Concurrent Operations**: Limited to 3 simultaneous generations

## Caching Strategy

- Research results cached for 24 hours
- Tests cached based on company and creation time
- Force regeneration option available
- Database-level caching for frequently accessed tests

## Next Steps

The AI services are now ready for integration with:
1. Test management endpoints (Task 5)
2. User dashboard and company selection (Task 6)
3. Frontend test interface (Task 7)

## Troubleshooting

**Common Issues:**

1. **Missing API Keys**: Ensure SONAR_API_KEY and GEMINI_API_KEY are set
2. **Network Timeouts**: Check internet connectivity and API service status
3. **Rate Limits**: Implement appropriate delays between requests
4. **Database Errors**: Ensure database is properly initialized and accessible

**Logs**: Check application logs for detailed error information and debugging.