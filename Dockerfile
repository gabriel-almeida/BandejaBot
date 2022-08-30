FROM python:3.10.6-slim
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .
CMD python BandejaBot.py $TOKEN $ID_MESTRE $PORT $URL