FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y \
        libglib2.0-0 \
        libsm6 \
        libxrender1 \
        libxext6 \
        libgl1 \
        poppler-utils \
        tesseract-ocr \
        libpq-dev \
        gcc \
        build-essential \
        && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

RUN python3 -m nltk.downloader -d /app/nltk_data averaged_perceptron_tagger punkt
ENV NLTK_DATA=/app/nltk_data

ENV FONTCONFIG_CACHE=/tmp/.fontconfig
ENV TRANSFORMERS_CACHE=/app/models
ENV HF_HOME=/app/models
ENV SENTENCE_TRANSFORMERS_HOME=/app/models

# For donwloading files for the first time
RUN python test.py 552

# Set the command for AWS Lambda
ENTRYPOINT [ "/usr/local/bin/python", "-m", "awslambdaric" ]
CMD [ "lambda_function.lambda_handler" ]
