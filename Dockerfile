FROM ubuntu:20.04

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update
RUN apt-get install -y vim netcat git docker.io docker-compose python3 python3-pip
COPY . /app/d2-docker
RUN pip3 install /app/d2-docker

ENTRYPOINT ["/app/d2-docker/docker-container/start.sh"]
CMD []
