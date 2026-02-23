# Minimal Shiny for Python on DigitalOcean App Platform
# Base: official Python image (Posit supports Python 3.8+; 3.12 is current LTS)
FROM python:3.12-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app and run script
COPY app.py run.sh .
RUN chmod +x run.sh

# Listen on all interfaces; use PORT from env (DigitalOcean sets this at runtime)
EXPOSE 8000
CMD ["./run.sh"]
