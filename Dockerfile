FROM ubuntu:16.04

ENV LANG C.UTF-8

RUN apt-get update > /dev/null
RUN apt-get install -y git > /dev/null
RUN apt-get install -y libopus-dev libssl-dev ffmpeg > /dev/null
RUN apt-get install -y python3 python3-pip > /dev/null

WORKDIR /app
COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY . .
RUN pip3 install pyinvoke > /dev/null
ENV PYTHONPATH=.
CMD python3 -m pyinvoke discord_gmusic_bot.main:main
