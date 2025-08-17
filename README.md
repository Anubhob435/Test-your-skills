# UEM Placement Preparation Platform

An AI-powered placement test preparation platform exclusively for University of Engineering and Management (UEM) students.

## Features

- 🤖 **AI-Powered Question Generation**: Dynamic questions using Perplexity AI research and Google Gemini
- 🏢 **Company-Specific Tests**: Tailored practice tests for TCS, Infosys, Capgemini, and more
- 📊 **Progress Tracking**: Detailed analytics and personalized recommendations
- 🔐 **UEM-Exclusive Access**: Only @uem.edu.in email addresses allowed
- 📱 **Responsive Design**: Works seamlessly on desktop and mobile devices

## Technology Stack

- **Backend**: Flask (Python 3.8+)
- **Database**: PostgreSQL (with SQLite fallback for development)
- **Authentication**: Flask-Login with JWT tokens
- **Frontend**: HTML5, TailwindCSS, Vanilla JavaScript
- **External APIs**: Perplexity AI, Google Gemini
- **Deployment**: Vercel (serverless functions)

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- PostgreSQL (optional, SQLite used by default in development)
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd uem-placement-platform
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   
   # On Windows
   .venv\Scripts\activate
   
   # On macOS/Linux
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   
   Copy the existing `.env` file or create a new one with:
   ```env
   # API Keys
   GEMINI_API_KEY=your_gemini_api_key_here
   SONAR_API_KEY=your_perplexity_api_key_here
   
   # Database (optional - SQLite used by default)
   DATABASE_URL=postgresql://username:password@localhost/uem_placement
   
   # Security
   SECRET_KEY=your_secret_key_here
   JWT_SECRET_KEY=your_jwt_secret_key_here
   
   # Environment
   FLASK_ENV=development
   ```

5. **Initialize the database**
   ```bash
   python init_db.py
   ```

6. **Run the application**
   ```bash
   # Using the run script
   python run.py
   
   # Or directly
   python app.py
   ```

7. **Access the application**
   
   Open your browser and navigate to `http://localhost:5000`

### Development Setup

For development with auto-reload:

```bash
export FLASK_ENV=development
export FLASK_APP=app.py
flask run --debug
```

### Database Migrations

If you make changes to the models, create and apply migrations:

```bash
# Create migration
flask db migrate -m "Description of changes"

# Apply migration
flask db upgrade
```

## Project Structure

```
uem-placement-platform/
├── app.py                 # Main Flask application
├── config.py             # Configuration settings
├── models.py             # Database models
├── init_db.py           # Database initialization script
├── run.py               # Development server runner
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables
├── .gitignore          # Git ignore rules
├── README.md           # This file
├── static/             # Static assets
│   ├── css/
│   │   └── custom.css  # Custom styles
│   ├── js/
│   │   └── utils.js    # JavaScript utilities
│   └── images/         # Image assets
├── templates/          # Jinja2 templates
│   ├── base.html      # Base template
│   └── index.html     # Home page
└── migrations/        # Database migrations (auto-generated)
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout
- `GET /api/auth/profile` - Get user profile

### Tests
- `GET /api/companies` - List available companies
- `POST /api/tests/generate/{company}` - Generate new test
- `GET /api/tests/{test_id}` - Get test questions
- `POST /api/tests/{test_id}/submit` - Submit test answers

### Health Check
- `GET /health` - Application health status

## Development Guidelines

### Code Style
- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Keep functions small and focused

### Database
- Use SQLAlchemy ORM for database operations
- Create migrations for schema changes
- Use proper indexes for performance
- Validate data before database operations

### Security
- Validate all user inputs
- Use parameterized queries to prevent SQL injection
- Implement proper authentication and authorization
- Store sensitive data in environment variables

### Testing
- Write unit tests for all business logic
- Test API endpoints with different scenarios
- Use pytest for testing framework
- Maintain good test coverage

## Deployment

### Vercel Deployment

1. **Install Vercel CLI**
   ```bash
   npm install -g vercel
   ```

2. **Configure vercel.json**
   
   The project includes a `vercel.json` configuration file.

3. **Deploy**
   ```bash
   vercel --prod
   ```

### Environment Variables for Production

Set these environment variables in your production environment:

- `FLASK_ENV=production`
- `DATABASE_URL` - PostgreSQL connection string
- `GEMINI_API_KEY` - Google Gemini API key
- `SONAR_API_KEY` - Perplexity AI API key
- `SECRET_KEY` - Flask secret key
- `JWT_SECRET_KEY` - JWT signing key

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support and questions, please contact the development team or create an issue in the repository.