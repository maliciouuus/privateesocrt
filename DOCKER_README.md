# Docker Setup and CI/CD Documentation

This document provides instructions on how to use the Docker setup and the GitHub Actions CI/CD pipeline for this project.

## Docker Setup

### Prerequisites

- Docker and Docker Compose installed on your machine
- Git installed on your machine

### Running the Application with Docker Compose

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Create a `.env` file in the root directory with the following variables:
   ```
   # Database settings
   user=your_db_user
   password=your_db_password
   host=db
   dbname=your_db_name
   
   # Django settings
   DEBUG=False
   SECRET_KEY=your_secret_key
   ALLOWED_HOSTS=localhost,127.0.0.1
   ```

3. Start the application using Docker Compose:
   ```bash
   docker-compose up -d
   ```

4. The application should now be running at `http://localhost:80`

### Building the Docker Image Manually

If you want to build the Docker image manually:

```bash
docker build -t your-image-name:tag .
```

### Running Database Migrations

After the containers are up, you may need to apply migrations:

```bash
docker-compose exec web python manage.py migrate
```

### Creating a Superuser

To create a superuser for the Django admin:

```bash
docker-compose exec web python manage.py createsuperuser
```

## CI/CD Pipeline

This project uses GitHub Actions for CI/CD. The workflow is defined in `.github/workflows/oc-lettings-pipeline.yml`.

### Workflow Steps

1. **Test and Lint**:
   - Runs flake8 for code linting
   - Executes pytest with coverage reports
   - Ensures at least 80% test coverage

2. **Build and Push Docker Image**:
   - Builds the Docker image from the Dockerfile
   - Pushes the image to Docker Hub with both `latest` and commit SHA tags
   - Only runs on pushes to the main/master branch

### Required Secrets

For the workflow to function properly, you need to set up the following secrets in your GitHub repository:

- `DOCKER_USERNAME`: Your Docker Hub username
- `DOCKER_PASSWORD`: Your Docker Hub password or access token

### Setting Up Secrets

1. Go to your GitHub repository
2. Click on "Settings" > "Secrets and variables" > "Actions"
3. Click on "New repository secret"
4. Add each secret with its respective value

## Development Workflow

1. Create a feature branch from main/master
2. Make your changes
3. Run tests locally using pytest
4. Create a pull request to main/master
5. The CI/CD pipeline will run tests on your PR
6. Once approved and merged, the pipeline will automatically build and push a new Docker image

## Deployment

The Docker image is automatically published to Docker Hub at `purityoff/oc-lettings:latest` and `purityoff/oc-lettings:<commit-sha>`.

To deploy the latest version:

```bash
docker pull purityoff/oc-lettings:latest
```

Or to deploy a specific version:

```bash
docker pull purityoff/oc-lettings:<commit-sha>
```

## Health Checks

The application includes health check endpoints:

- `/health/` - Returns a 200 OK response when the application is running

These endpoints are used by Docker Compose and can also be used in production environments for monitoring. 