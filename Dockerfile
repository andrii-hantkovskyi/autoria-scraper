FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y cron curl gnupg2 && \
    curl -s https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - && \
    echo "deb http://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
    apt-get update && \
    apt-get install -y postgresql-client-17 build-essential libpq-dev && \
    apt-get clean

WORKDIR /app

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install-deps && playwright install

COPY app/ /app

COPY crontab /etc/cron.d/scraper-cron
RUN chmod 0644 /etc/cron.d/scraper-cron && crontab /etc/cron.d/scraper-cron

RUN touch /var/log/cron.log

CMD ["cron", "-f"]
