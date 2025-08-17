from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

# This will be set by the app
db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for UEM students"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer)
    branch = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    
    # Relationships
    test_attempts = db.relationship('TestAttempt', backref='user', lazy=True, cascade='all, delete-orphan')
    progress_metrics = db.relationship('ProgressMetrics', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        from auth_service import AuthService
        self.password_hash = AuthService.hash_password(password)
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        from auth_service import AuthService
        return AuthService.verify_password(password, self.password_hash)
    
    def is_uem_email(self):
        """Check if email belongs to UEM domain"""
        return self.email.endswith('@uem.edu.in')
    
    def to_dict(self):
        """Convert user to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'year': self.year,
            'branch': self.branch,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_admin': self.is_admin
        }
    
    def __repr__(self):
        return f'<User {self.email}>'

class Test(db.Model):
    """Test model for company-specific placement tests"""
    __tablename__ = 'tests'
    
    id = db.Column(db.Integer, primary_key=True)
    company = db.Column(db.String(100), nullable=False, index=True)
    year = db.Column(db.Integer, default=2025, index=True)
    pattern_data = db.Column(db.Text)  # JSON string of test pattern info
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    questions = db.relationship('Question', backref='test', lazy=True, cascade='all, delete-orphan')
    test_attempts = db.relationship('TestAttempt', backref='test', lazy=True, cascade='all, delete-orphan')
    
    def get_pattern_data(self):
        """Get pattern data as dictionary"""
        if self.pattern_data:
            return json.loads(self.pattern_data)
        return {}
    
    def set_pattern_data(self, data):
        """Set pattern data from dictionary"""
        self.pattern_data = json.dumps(data)
    
    def to_dict(self):
        """Convert test to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'company': self.company,
            'year': self.year,
            'pattern_data': self.get_pattern_data(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'question_count': len(self.questions)
        }
    
    def __repr__(self):
        return f'<Test {self.company} {self.year}>'

class Question(db.Model):
    """Question model for test questions"""
    __tablename__ = 'questions'
    
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('tests.id'), nullable=False, index=True)
    section = db.Column(db.String(50), nullable=False, index=True)  # e.g., 'Quantitative Aptitude', 'Logical Reasoning'
    question_text = db.Column(db.Text, nullable=False)
    options = db.Column(db.JSON, nullable=False)  # List of options
    correct_answer = db.Column(db.String(10), nullable=False)  # Index or letter of correct option
    explanation = db.Column(db.Text)
    difficulty = db.Column(db.String(20), default='medium', index=True)  # easy, medium, hard
    topic = db.Column(db.String(100), index=True)  # Specific topic within section
    
    def to_dict(self, include_answer=False):
        """Convert question to dictionary for JSON serialization"""
        data = {
            'id': self.id,
            'section': self.section,
            'question_text': self.question_text,
            'options': self.options,
            'difficulty': self.difficulty,
            'topic': self.topic
        }
        
        if include_answer:
            data['correct_answer'] = self.correct_answer
            data['explanation'] = self.explanation
        
        return data
    
    def __repr__(self):
        return f'<Question {self.id} - {self.section}>'

class TestAttempt(db.Model):
    """Test attempt model to track user test submissions"""
    __tablename__ = 'test_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    test_id = db.Column(db.Integer, db.ForeignKey('tests.id'), nullable=False, index=True)
    score = db.Column(db.Float, nullable=False, index=True)
    total_questions = db.Column(db.Integer, nullable=False)
    time_taken = db.Column(db.Integer)  # Time in seconds
    answers = db.Column(db.JSON)  # User's answers as JSON
    started_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    completed_at = db.Column(db.DateTime, index=True)
    
    def get_answers(self):
        """Get answers as dictionary"""
        if self.answers:
            return self.answers
        return {}
    
    def set_answers(self, answers_dict):
        """Set answers from dictionary"""
        self.answers = answers_dict
    
    def calculate_percentage(self):
        """Calculate percentage score"""
        if self.total_questions > 0:
            return (self.score / self.total_questions) * 100
        return 0
    
    def to_dict(self):
        """Convert test attempt to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'test_id': self.test_id,
            'score': self.score,
            'total_questions': self.total_questions,
            'percentage': self.calculate_percentage(),
            'time_taken': self.time_taken,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'answers': self.get_answers()
        }
    
    def __repr__(self):
        return f'<TestAttempt {self.id} - User {self.user_id} - Test {self.test_id}>'

class ProgressMetrics(db.Model):
    """Progress metrics model to track user performance by subject area"""
    __tablename__ = 'progress_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    subject_area = db.Column(db.String(50), nullable=False)  # e.g., 'Quantitative Aptitude'
    accuracy_rate = db.Column(db.Float, default=0.0)  # Percentage accuracy
    total_attempts = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint to prevent duplicate entries
    __table_args__ = (db.UniqueConstraint('user_id', 'subject_area', name='unique_user_subject'),)
    
    def update_metrics(self, new_score, total_questions):
        """Update metrics with new test results"""
        # Calculate new accuracy rate
        current_total_correct = (self.accuracy_rate / 100) * self.total_attempts * total_questions
        new_total_correct = current_total_correct + new_score
        new_total_attempts = self.total_attempts + 1
        
        self.accuracy_rate = (new_total_correct / (new_total_attempts * total_questions)) * 100
        self.total_attempts = new_total_attempts
        self.last_updated = datetime.utcnow()
    
    def to_dict(self):
        """Convert progress metrics to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'subject_area': self.subject_area,
            'accuracy_rate': round(self.accuracy_rate, 2),
            'total_attempts': self.total_attempts,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }
    
    def __repr__(self):
        return f'<ProgressMetrics User {self.user_id} - {self.subject_area}>'