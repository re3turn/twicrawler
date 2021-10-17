FROM python:3.7-alpine

WORKDIR /app
COPY requirements.txt .

RUN apk add --no-cache --virtual build-deps build-base libffi-dev \
  && apk add --no-cache postgresql-dev \
  && pip install --no-cache-dir -r requirements.txt \
  && apk del build-deps

COPY app ./app
COPY run.py .
COPY get_refresh_token.py .

CMD ["python", "./run.py"]
