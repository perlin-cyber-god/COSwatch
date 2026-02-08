# Use a lightweight Python image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file first to use Docker's cache
COPY requirements.txt .

# Install all dependencies (FastAPI, Supabase, etc.)
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of Sundeep's backend code
COPY . .

# Use uvicorn to run the app and keep the container running
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]