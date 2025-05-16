# Use an official Python runtime as a parent image
FROM python:3.11

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container at /usr/src/app
COPY . .

# Install any needed packages specified in requirements.txt
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN apt update && apt install ffmpeg -y

# Expose port 8080 for the application
EXPOSE 8025

# Define environment variable
ENV PORT 8025

# Run adguard-web.py when the container launches
CMD ["python", "serve.py"]
