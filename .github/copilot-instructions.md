# GitHub Copilot Instructions

## Language Rule

- **Always respond in Korean.**
- Regardless of the input language, always reply in Korean.
- When performing a code review, ALWAYS respond in Korean.

# GitHub Copilot Instructions

## Tech Stack

- We use FastAPI for backend, not Flask or Django
- Database: PostgreSQL with SQLModel and SQLAlchemy ORM
- Frontend: Flutter
- Deployment: Docker-compose
- AI: Google Gemini API

## Code Review Rule

- When reviewing code or proposing changes, **always include a `suggestion` block**
- Check for security vulnerabilities (SQL injection, XSS, etc.)
- Verify proper error handling
- Ensure test coverage for new features
- Check for code duplication (DRY principle)
