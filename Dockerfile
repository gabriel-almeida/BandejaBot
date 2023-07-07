FROM python:3.10.6-slim
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY BandejaBot.py BandejaBot.py
COPY Cardapio.py Cardapio.py

EXPOSE 3000
CMD python BandejaBot.py