FROM python:3.10.6-slim
WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY BandejaBot.py BandejaBot.py
COPY Cardapio.py Cardapio.py
COPY healthcheck.sh healthcheck.sh

RUN chmod +x healthcheck.sh

EXPOSE 3000
CMD python BandejaBot.py