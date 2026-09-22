# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /code

# Copy the dependencies file to the working directory
COPY ./requirements.txt /code/requirements.txt

# Install dependencies
# --no-cache-dir keeps the image small
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the content of the local src directory to the working directory
COPY ./app /code/app

# Set environment variable for Cloud Run (PORT usually defaults to 8080)
ENV PORT=8080

# Command to run the application using Uvicorn
# host 0.0.0.0 is required for running inside Docker
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]