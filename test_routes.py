"""
Test Management Routes for UEM Placement Platform
Handles test creation, retrieval, and submission endpoints
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import BadRequest

from models import db, Test, Question, TestAttempt, ProgressMetrics, User
from question_generation_service import QuestionGenerationService, QuestionGenerationError
from auth_middleware import jwt_required_custom, get_current_user

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
test_bp = Blueprint('test', __name__, url_prefix='/api/tests')

# Initialize question generation service
question_service = QuestionGenerationService()

# Company configuration
SUPPORTED_COMPANIES = [
    'TCS NQT', 'Infosys', 'Capgemini', 'Wipro', 'Accenture', 
    'Cognizant', 'HCL', 'Tech Mahindra', 'IBM', 'Microsoft',
    'Amazon', 'Google', 'Deloitte', 'EY', 'KPMG', 'PwC'
]

DEFAULT_TEST_CONFIG = {
    'time_limit_minutes': 60,
    'questions_per_test': 20,
    'sections': {
        'Quantitative Aptitude': {'questions': 8, 'time_minutes': 25},
        'Logical Reasoning': {'questions': 7, 'time_minutes': 20},
        'Verbal Ability': {'questions': 5, 'time_minutes': 15}
    }
}

@test_bp.route('/generate/<string:company>', methods=['POST'])
@jwt_required_custom()
def generate_test(company):
    """
    Generate a new test for a specific company
    
    POST /api/tests/generate/{company}
    
    Request Body (optional):
    {
        "num_questions": 20,
        "year": 2025,
        "force_regenerate": false
    }
    
    Response:
    {
        "success": true,
        "test_id": 123,
        "company": "TCS NQT",
        "num_questions": 20,
        "created_at": "2025-01-17T10:30:00Z",
        "from_cache": false,
        "generation_time": 45.2,
        "sections": ["Quantitative Aptitude", "Logical Reasoning"]
    }
    """
    try:
        # Validate company name
        if not company or company.strip() == '':
            return jsonify({
                'error': True,
                'message': 'Company name is required',
                'code': 'INVALID_COMPANY'
            }), 400
        
        # Clean and validate company name
        company = company.strip()
        
        # Get request parameters
        data = request.get_json() or {}
        num_questions = data.get('num_questions', DEFAULT_TEST_CONFIG['questions_per_test'])
        year = data.get('year', 2025)
        force_regenerate = data.get('force_regenerate', False)
        
        # Validate parameters
        if not isinstance(num_questions, int) or num_questions < 5 or num_questions > 50:
            return jsonify({
                'error': True,
                'message': 'Number of questions must be between 5 and 50',
                'code': 'INVALID_QUESTION_COUNT'
            }), 400
        
        if not isinstance(year, int) or year < 2020 or year > 2030:
            return jsonify({
                'error': True,
                'message': 'Year must be between 2020 and 2030',
                'code': 'INVALID_YEAR'
            }), 400
        
        current_user = get_current_user()
        logger.info(f"User {current_user.id} requested test generation for {company}")
        
        # Generate test using question generation service
        try:
            result = question_service.generate_test_sync(
                company=company,
                num_questions=num_questions,
                year=year,
                force_regenerate=force_regenerate
            )
            
            # Add company configuration to result
            result['config'] = {
                'time_limit_minutes': DEFAULT_TEST_CONFIG['time_limit_minutes'],
                'company_info': {
                    'name': company,
                    'supported': company in SUPPORTED_COMPANIES
                }
            }
            
            logger.info(f"Test generated successfully for {company} (Test ID: {result['test_id']})")
            
            return jsonify(result), 201
            
        except QuestionGenerationError as e:
            logger.error(f"Question generation failed for {company}: {e}")
            return jsonify({
                'error': True,
                'message': f'Failed to generate test: {str(e)}',
                'code': 'GENERATION_FAILED'
            }), 500
        
    except BadRequest as e:
        return jsonify({
            'error': True,
            'message': 'Invalid request format',
            'code': 'BAD_REQUEST'
        }), 400
    except Exception as e:
        logger.error(f"Unexpected error in test generation: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@test_bp.route('/<int:test_id>', methods=['GET'])
@jwt_required_custom()
def get_test(test_id):
    """
    Retrieve a test by ID with questions for taking the test
    
    GET /api/tests/{test_id}
    
    Query Parameters:
    - include_answers: boolean (default: false) - Include correct answers (for admin)
    - randomize: boolean (default: true) - Randomize question order
    - section: string (optional) - Filter by specific section
    
    Response:
    {
        "test_id": 123,
        "company": "TCS NQT",
        "year": 2025,
        "total_questions": 20,
        "time_limit_minutes": 60,
        "sections": [
            {
                "section_name": "Quantitative Aptitude",
                "questions": [
                    {
                        "id": 1,
                        "question_text": "What is 2+2?",
                        "options": ["3", "4", "5", "6"],
                        "difficulty": "easy"
                    }
                ]
            }
        ],
        "metadata": {
            "created_at": "2025-01-17T10:30:00Z",
            "user_attempts": 2
        }
    }
    """
    try:
        # Get query parameters
        include_answers = request.args.get('include_answers', 'false').lower() == 'true'
        randomize = request.args.get('randomize', 'true').lower() == 'true'
        section_filter = request.args.get('section')
        
        current_user = get_current_user()
        
        # Only admins can include answers
        if include_answers and not current_user.is_admin:
            return jsonify({
                'error': True,
                'message': 'Insufficient permissions to view answers',
                'code': 'INSUFFICIENT_PERMISSIONS'
            }), 403
        
        # Retrieve test from database
        test = Test.query.get(test_id)
        if not test:
            return jsonify({
                'error': True,
                'message': 'Test not found',
                'code': 'TEST_NOT_FOUND'
            }), 404
        
        # Build query for questions
        questions_query = Question.query.filter_by(test_id=test_id)
        
        # Apply section filter if specified
        if section_filter:
            questions_query = questions_query.filter(Question.section.ilike(f'%{section_filter}%'))
        
        # Get questions
        questions = questions_query.all()
        
        if not questions:
            return jsonify({
                'error': True,
                'message': 'No questions found for this test',
                'code': 'NO_QUESTIONS'
            }), 404
        
        # Group questions by section
        sections_data = {}
        for question in questions:
            section_name = question.section
            if section_name not in sections_data:
                sections_data[section_name] = []
            
            question_data = question.to_dict(include_answer=include_answers)
            sections_data[section_name].append(question_data)
        
        # Randomize questions within sections if requested
        if randomize:
            import random
            for section_questions in sections_data.values():
                random.shuffle(section_questions)
        
        # Format sections for response
        sections = []
        for section_name, section_questions in sections_data.items():
            sections.append({
                'section_name': section_name,
                'question_count': len(section_questions),
                'questions': section_questions
            })
        
        # Get user's previous attempts for this test
        user_attempts = TestAttempt.query.filter_by(
            user_id=current_user.id,
            test_id=test_id
        ).count()
        
        # Prepare response
        response_data = {
            'test_id': test.id,
            'company': test.company,
            'year': test.year,
            'total_questions': len(questions),
            'time_limit_minutes': DEFAULT_TEST_CONFIG['time_limit_minutes'],
            'sections': sections,
            'metadata': {
                'created_at': test.created_at.isoformat(),
                'user_attempts': user_attempts,
                'pattern_data': test.get_pattern_data() if current_user.is_admin else None
            }
        }
        
        logger.info(f"User {current_user.id} retrieved test {test_id} ({test.company})")
        
        return jsonify(response_data), 200
        
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving test {test_id}: {e}")
        return jsonify({
            'error': True,
            'message': 'Database error',
            'code': 'DATABASE_ERROR'
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error retrieving test {test_id}: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@test_bp.route('/<int:test_id>/submit', methods=['POST'])
@jwt_required_custom()
def submit_test(test_id):
    """
    Submit test answers and calculate results
    
    POST /api/tests/{test_id}/submit
    
    Request Body:
    {
        "answers": {
            "1": "B",
            "2": "A",
            "3": "C"
        },
        "time_taken": 3600,
        "started_at": "2025-01-17T10:30:00Z"
    }
    
    Response:
    {
        "attempt_id": 456,
        "score": 15,
        "total_questions": 20,
        "percentage": 75.0,
        "time_taken": 3600,
        "results": [
            {
                "question_id": 1,
                "user_answer": "B",
                "correct_answer": "B",
                "is_correct": true,
                "explanation": "..."
            }
        ],
        "section_scores": {
            "Quantitative Aptitude": {"score": 6, "total": 8, "percentage": 75.0},
            "Logical Reasoning": {"score": 5, "total": 7, "percentage": 71.4}
        }
    }
    """
    try:
        # Validate request data
        data = request.get_json()
        if not data:
            return jsonify({
                'error': True,
                'message': 'Request body is required',
                'code': 'MISSING_DATA'
            }), 400
        
        answers = data.get('answers', {})
        time_taken = data.get('time_taken')
        started_at_str = data.get('started_at')
        
        if not answers:
            return jsonify({
                'error': True,
                'message': 'Answers are required',
                'code': 'MISSING_ANSWERS'
            }), 400
        
        # Validate test exists
        test = Test.query.get(test_id)
        if not test:
            return jsonify({
                'error': True,
                'message': 'Test not found',
                'code': 'TEST_NOT_FOUND'
            }), 404
        
        # Get all questions for this test
        questions = Question.query.filter_by(test_id=test_id).all()
        if not questions:
            return jsonify({
                'error': True,
                'message': 'No questions found for this test',
                'code': 'NO_QUESTIONS'
            }), 404
        
        # Calculate results
        total_questions = len(questions)
        correct_answers = 0
        results = []
        section_scores = {}
        
        logger.info(f"Processing {total_questions} questions for test {test_id}")
        
        for question in questions:
            try:
                question_id_str = str(question.id)
                user_answer_raw = answers.get(question_id_str, '')
                
                # Handle None or non-string user answers
                if user_answer_raw is None:
                    user_answer = ''
                else:
                    user_answer = str(user_answer_raw).strip().upper()
                
                # Handle None correct_answer (shouldn't happen but be safe)
                if question.correct_answer is None:
                    logger.warning(f"Question {question.id} has None correct_answer")
                    correct_answer = ''
                else:
                    correct_answer = str(question.correct_answer).strip().upper()
                
                is_correct = user_answer == correct_answer and user_answer != ''
                
            except Exception as e:
                logger.error(f"Error processing question {question.id}: {e}")
                logger.error(f"Question data: correct_answer={repr(question.correct_answer)}, user_answer_raw={repr(user_answer_raw)}")
                raise
            
            if is_correct:
                correct_answers += 1
            
            # Track section scores
            section = question.section
            if section not in section_scores:
                section_scores[section] = {'correct': 0, 'total': 0}
            
            section_scores[section]['total'] += 1
            if is_correct:
                section_scores[section]['correct'] += 1
            
            # Add to results
            results.append({
                'question_id': question.id,
                'section': section,
                'user_answer': user_answer,
                'correct_answer': correct_answer,
                'is_correct': is_correct,
                'explanation': question.explanation,
                'question_text': question.question_text,
                'options': question.options
            })
        
        current_user = get_current_user()
        
        # Calculate percentage
        percentage = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
        
        # Parse started_at if provided
        started_at = None
        if started_at_str:
            try:
                started_at = datetime.fromisoformat(started_at_str.replace('Z', '+00:00'))
            except ValueError:
                logger.warning(f"Invalid started_at format: {started_at_str}")
        
        # Create test attempt record
        test_attempt = TestAttempt(
            user_id=current_user.id,
            test_id=test_id,
            score=correct_answers,
            total_questions=total_questions,
            time_taken=time_taken,
            answers=answers,
            started_at=started_at or datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        
        db.session.add(test_attempt)
        db.session.flush()  # Get attempt ID
        
        # Update progress metrics for each section
        for section, scores in section_scores.items():
            section_percentage = (scores['correct'] / scores['total']) * 100 if scores['total'] > 0 else 0
            
            # Find or create progress metric
            progress_metric = ProgressMetrics.query.filter_by(
                user_id=current_user.id,
                subject_area=section
            ).first()
            
            if progress_metric:
                # Update existing metric
                progress_metric.update_metrics(scores['correct'], scores['total'])
            else:
                # Create new metric
                progress_metric = ProgressMetrics(
                    user_id=current_user.id,
                    subject_area=section,
                    accuracy_rate=section_percentage,
                    total_attempts=1
                )
                db.session.add(progress_metric)
        
        # Commit all changes
        db.session.commit()
        
        # Format section scores for response
        formatted_section_scores = {}
        for section, scores in section_scores.items():
            section_percentage = (scores['correct'] / scores['total']) * 100 if scores['total'] > 0 else 0
            formatted_section_scores[section] = {
                'score': scores['correct'],
                'total': scores['total'],
                'percentage': round(section_percentage, 1)
            }
        
        # Prepare response
        response_data = {
            'attempt_id': test_attempt.id,
            'score': correct_answers,
            'total_questions': total_questions,
            'percentage': round(percentage, 1),
            'time_taken': time_taken,
            'completed_at': test_attempt.completed_at.isoformat(),
            'results': results,
            'section_scores': formatted_section_scores,
            'test_info': {
                'company': test.company,
                'year': test.year
            }
        }
        
        logger.info(f"User {current_user.id} submitted test {test_id} - Score: {correct_answers}/{total_questions} ({percentage:.1f}%)")
        
        return jsonify(response_data), 200
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error submitting test {test_id}: {e}")
        return jsonify({
            'error': True,
            'message': 'Database error',
            'code': 'DATABASE_ERROR'
        }), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error submitting test {test_id}: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@test_bp.route('/companies', methods=['GET'])
@jwt_required_custom()
def get_companies():
    """
    Get list of available companies with test statistics
    
    GET /api/tests/companies
    
    Response:
    {
        "companies": [
            {
                "name": "TCS NQT",
                "test_count": 3,
                "latest_test": "2025-01-17T10:30:00Z",
                "supported": true
            }
        ],
        "total_companies": 16,
        "supported_companies": ["TCS NQT", "Infosys", ...]
    }
    """
    try:
        # Get test statistics from database
        company_stats = db.session.query(
            Test.company,
            db.func.count(Test.id).label('test_count'),
            db.func.max(Test.created_at).label('latest_test')
        ).group_by(Test.company).all()
        
        # Format company data
        companies = []
        for stat in company_stats:
            companies.append({
                'name': stat.company,
                'test_count': stat.test_count,
                'latest_test': stat.latest_test.isoformat() if stat.latest_test else None,
                'supported': stat.company in SUPPORTED_COMPANIES
            })
        
        # Add supported companies that don't have tests yet
        existing_companies = {stat.company for stat in company_stats}
        for company in SUPPORTED_COMPANIES:
            if company not in existing_companies:
                companies.append({
                    'name': company,
                    'test_count': 0,
                    'latest_test': None,
                    'supported': True
                })
        
        # Sort by name
        companies.sort(key=lambda x: x['name'])
        
        response_data = {
            'companies': companies,
            'total_companies': len(companies),
            'supported_companies': SUPPORTED_COMPANIES
        }
        
        return jsonify(response_data), 200
        
    except SQLAlchemyError as e:
        logger.error(f"Database error getting companies: {e}")
        return jsonify({
            'error': True,
            'message': 'Database error',
            'code': 'DATABASE_ERROR'
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error getting companies: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@test_bp.route('/<int:test_id>/results/<int:attempt_id>', methods=['GET'])
@jwt_required_custom()
def get_test_results(test_id, attempt_id):
    """
    Get detailed results for a specific test attempt
    
    GET /api/tests/{test_id}/results/{attempt_id}
    
    Response:
    {
        "attempt_id": 456,
        "test_info": {
            "test_id": 123,
            "company": "TCS NQT",
            "year": 2025
        },
        "score": 15,
        "total_questions": 20,
        "percentage": 75.0,
        "time_taken": 3600,
        "completed_at": "2025-01-17T11:30:00Z",
        "results": [...],
        "section_scores": {...}
    }
    """
    try:
        current_user = get_current_user()
        
        # Validate test attempt exists and belongs to current user
        test_attempt = TestAttempt.query.filter_by(
            id=attempt_id,
            test_id=test_id,
            user_id=current_user.id
        ).first()
        
        if not test_attempt:
            return jsonify({
                'error': True,
                'message': 'Test attempt not found or access denied',
                'code': 'ATTEMPT_NOT_FOUND'
            }), 404
        
        # Get test info
        test = Test.query.get(test_id)
        if not test:
            return jsonify({
                'error': True,
                'message': 'Test not found',
                'code': 'TEST_NOT_FOUND'
            }), 404
        
        # Get questions for detailed results
        questions = Question.query.filter_by(test_id=test_id).all()
        questions_dict = {q.id: q for q in questions}
        
        # Build detailed results
        results = []
        section_scores = {}
        user_answers = test_attempt.get_answers()
        
        for question in questions:
            question_id_str = str(question.id)
            user_answer = user_answers.get(question_id_str, '').strip().upper()
            correct_answer = question.correct_answer.strip().upper()
            is_correct = user_answer == correct_answer
            
            # Track section scores
            section = question.section
            if section not in section_scores:
                section_scores[section] = {'correct': 0, 'total': 0}
            
            section_scores[section]['total'] += 1
            if is_correct:
                section_scores[section]['correct'] += 1
            
            results.append({
                'question_id': question.id,
                'section': section,
                'question_text': question.question_text,
                'options': question.options,
                'user_answer': user_answer,
                'correct_answer': correct_answer,
                'is_correct': is_correct,
                'explanation': question.explanation,
                'difficulty': question.difficulty
            })
        
        # Format section scores
        formatted_section_scores = {}
        for section, scores in section_scores.items():
            section_percentage = (scores['correct'] / scores['total']) * 100 if scores['total'] > 0 else 0
            formatted_section_scores[section] = {
                'score': scores['correct'],
                'total': scores['total'],
                'percentage': round(section_percentage, 1)
            }
        
        response_data = {
            'attempt_id': test_attempt.id,
            'test_info': {
                'test_id': test.id,
                'company': test.company,
                'year': test.year
            },
            'score': test_attempt.score,
            'total_questions': test_attempt.total_questions,
            'percentage': test_attempt.calculate_percentage(),
            'time_taken': test_attempt.time_taken,
            'started_at': test_attempt.started_at.isoformat() if test_attempt.started_at else None,
            'completed_at': test_attempt.completed_at.isoformat() if test_attempt.completed_at else None,
            'results': results,
            'section_scores': formatted_section_scores
        }
        
        return jsonify(response_data), 200
        
    except SQLAlchemyError as e:
        logger.error(f"Database error getting test results {attempt_id}: {e}")
        return jsonify({
            'error': True,
            'message': 'Database error',
            'code': 'DATABASE_ERROR'
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error getting test results {attempt_id}: {e}")
        return jsonify({
            'error': True,
            'message': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

# Error handlers for the blueprint
@test_bp.errorhandler(404)
def test_not_found(error):
    return jsonify({
        'error': True,
        'message': 'Test endpoint not found',
        'code': 'ENDPOINT_NOT_FOUND'
    }), 404

@test_bp.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        'error': True,
        'message': 'Method not allowed',
        'code': 'METHOD_NOT_ALLOWED'
    }), 405