FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get install -y vim netcat-openbsd git docker.io docker-compose-v2 python3 python3-pip python3-venv
COPY . /app/d2-docker
# Ubuntu 24.04 does not allow pip installs into the system Python (PEP 668)
RUN python3 -m venv /opt/d2-docker && /opt/d2-docker/bin/pip install /app/d2-docker
ENV PATH="/opt/d2-docker/bin:$PATH"

ENTRYPOINT ["/app/d2-docker/docker-container/start.sh"]
CMD []
