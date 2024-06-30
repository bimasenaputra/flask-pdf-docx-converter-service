FROM python:3.9.19-slim

ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./

RUN apt-get update && \
    apt-get --no-install-recommends install libreoffice -y && \
    apt-get install -y libreoffice-java-common default-jre && \
    pip install --default-timeout=1400 --no-cache-dir -r requirements.txt

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app