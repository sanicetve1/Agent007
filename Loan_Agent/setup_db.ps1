# Stop and remove any existing container
Write-Host "Stopping existing container..."
docker stop loan-postgres -ErrorAction SilentlyContinue
docker rm loan-postgres -ErrorAction SilentlyContinue

# Remove existing volume (optional: uncomment if you want full reset)
# docker volume rm loan-agent_postgres_data

# Start container with docker-compose
Write-Host "Starting new PostgreSQL container..."
docker-compose up -d

# Wait for Postgres to start
Write-Host "Waiting 10 seconds for Postgres to initialize..."
Start-Sleep -Seconds 10

# Run SQL script inside container (just in case)
Write-Host "Running init.sql inside container..."
Get-Content .\DB\init.sql\init.sql | docker exec -i loan-postgres psql -U admin -d loan_db

# Verify tables
Write-Host "Verifying tables..."
docker exec -it loan-postgres psql -U admin -d loan_db -c "\dt"