aws ecr get-login-password --region ap-southeast-2 | docker login --username AWS --password-stdin 380206744475.dkr.ecr.ap-southeast-2.amazonaws.com

docker buildx build --provenance=false -t hyper-aigent-rag .

docker tag hyper-aigent-rag:latest 380206744475.dkr.ecr.ap-southeast-2.amazonaws.com/hyper-aigent-rag:latest

docker push 380206744475.dkr.ecr.ap-southeast-2.amazonaws.com/hyper-aigent-rag:latest

docker run -it --entrypoint /bin/bash hyper-aigent-rag

// works
FROM python:3.12-slim

# Install system dependencies

RUN apt-get update && \
 apt-get install -y \
 libglib2.0-0 \
 libsm6 \
 libxrender1 \
 libxext6 \
 poppler-utils \
 tesseract-ocr && \
 apt-get clean && \
 rm -rf /var/lib/apt/lists/\*

# Set working directory

WORKDIR /app

# Copy requirements and install

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app

COPY . .

# Set the command

CMD [ "lambda_function.lambda_handler" ]
