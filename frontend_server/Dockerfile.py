# Use the official Python image as the base
FROM python:3.10

# Set the working directory to /app
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY . .

# Set the command to run the application
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py setup_social_auth && python manage.py runserver 0.0.0.0:8000"]
