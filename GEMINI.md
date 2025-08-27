# Gemini Project Context: cashio-api

This document provides a foundational context for AI models interacting with the `cashio-api` project. Its purpose is to ensure that AI-generated code, analysis, and modifications align with the project's established standards and architecture.

## Project Overview

`cashio-api` is the backend API for the Cashio personal finance tracking application. It provides a set of RESTful endpoints to manage users, accounts, transactions, and other financial data. The API is built with Python using the FastAPI framework.

## Tech Stack

*   **Programming Language:** Python 3.13
*   **Framework:** FastAPI
*   **Database:** PostgreSQL
*   **ORM:** SQLAlchemy
*   **Authentication:** JWT with `python-jose`, `passlib`, and `bcrypt`
*   **Data Validation:** Pydantic
*   **API Server:** Uvicorn
*   **Dependency Management:** pip with `requirements.txt`
*   **Versioning:** `semantic-release`

## Project Structure

The `cashio-api` project follows a standard FastAPI project structure:

```
cashio-api/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application entry point
│   ├── version.py        # Project version
│   ├── database/
│   │   └── connection.py # SQLAlchemy database connection
│   ├── models/
│   │   └── model.py      # SQLAlchemy ORM models
│   ├── repositories/     # Data access layer (CRUD operations)
│   ├── routers/          # API endpoint definitions
│   ├── schemas/          # Pydantic schemas for data validation
│   └── security/         # Authentication and authorization logic
├── requirements.txt      # Project dependencies
├── pyproject.toml        # Project configuration, including semantic-release
├── Dockerfile            # Docker container definition
└── ...
```

*   **`app/main.py`**: The main entry point for the FastAPI application. It initializes the app, includes routers, and configures middleware.
*   **`app/database/`**: This directory contains the database connection and session management logic.
*   **`app/models/`**: Defines the SQLAlchemy ORM models that map to the database tables.
*   **`app/repositories/`**: The data access layer, responsible for all communication with the database (CRUD operations). This abstracts the database logic from the business logic in the routers.
*   **`app/routers/`**: Contains the API routers. Each router corresponds to a specific resource (e.g., users, accounts, transactions) and defines the API endpoints for that resource.
*   **`app/schemas/`**: Contains Pydantic schemas used for request and response data validation, serialization, and documentation.
*   **`app/security/`**: Implements authentication and authorization, including JWT generation and verification.

## Development Workflow

### Setup

1.  Create and activate a Python virtual environment.
2.  Install the dependencies: `pip install -r requirements.txt`
3.  Set up the required environment variables. A `.env` file can be used for this. Refer to `dotenv-template` for the required variables.

### Running the Application

To run the application for development, use the following command:

```bash
uvicorn app.main:app --reload --ssl-keyfile /path/to/key.pem --ssl-certfile /path/to/cert.pem
```

The application will be available at `https://localhost:8000`.

### Testing

The project does not currently have a dedicated test suite. When adding new features, please include corresponding tests.

## Coding Style & Conventions

*   Follow the PEP 8 style guide for Python code.
*   Use type hints for all function signatures.
*   Maintain the existing project structure. For new features, add new routers, repositories, and schemas as needed.
*   Use the repository pattern for all database interactions. Routers should not directly access the database.
*   Use Pydantic schemas for all API requests and responses.

## Deployment

The application is designed to be deployed as a Docker container. The `Dockerfile` in the root of the project defines the container image. The application is served by Uvicorn.

## Versioning and Releases

The project uses `semantic-release` for automated versioning and releases. Commit messages should follow the Conventional Commits specification.

*   `feat`: A new feature
*   `fix`: A bug fix
*   `docs`: Documentation only changes
*   `style`: Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc)
*   `refactor`: A code change that neither fixes a bug nor adds a feature
*   `perf`: A code change that improves performance
*   `test`: Adding missing tests or correcting existing tests
*   `build`: Changes that affect the build system or external dependencies
*   `ci`: Changes to our CI configuration files and scripts

This ensures that version numbers are bumped automatically and a changelog is generated based on the commit history.
