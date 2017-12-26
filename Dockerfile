FROM ubuntu:16.04

ENV LANG C.UTF-8

RUN apt-get update > /dev/null
RUN apt-get install -y libopus-dev libssl-dev ffmpeg > /dev/null
RUN apt-get install -y python3 python3-pip > /dev/null
RUN apt-get install -y git > /dev/null
RUN pip3 install git+https://github.com/nodepy/nodepy.git@develop > /dev/null
RUN nodepy https://nodepy.org/install-pm.py develop

WORKDIR /app
COPY nodepy.json nodepy.json
RUN nodepy-pm install

COPY . .
ENTRYPOINT nodepy .
