FROM python:3.8.0-alpine3.10

WORKDIR /app
COPY requirements.txt .

RUN apk add --no-cache --virtual build-deps build-base libffi-dev \
  && apk add --no-cache postgresql-dev \
  && pip install --no-cache-dir -r requirements.txt \
  && apk del build-deps

COPY app .
COPY run.py .

CMD ["python", "./run.py"]
