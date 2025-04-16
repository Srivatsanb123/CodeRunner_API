FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  curl \
  gnupg \
  gcc \
  g++ \
  openjdk-17-jdk && \
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
  apt-get install -y --no-install-recommends nodejs && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./

EXPOSE 5000

CMD ["python", "app.py"]
