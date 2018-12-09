FROM python:3.7-stretch

ENV LANG C.UTF-8

RUN apt-get update > /dev/null
RUN apt-get install -y git > /dev/null
RUN apt-get install -y libopus-dev libssl-dev ffmpeg > /dev/null

WORKDIR /app
COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY . .
RUN pip3 install -e .
ENV PYTHONPATH=.
CMD python3 -m quel.main -rv --prod
