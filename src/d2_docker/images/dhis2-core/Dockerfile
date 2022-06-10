FROM tomcat:9-jre11-temurin

ENV DHIS2_HOME=/DHIS2_home
ENV DATA_DIR=/data

COPY docker-entrypoint.sh /usr/local/bin/

RUN rm -rf /usr/local/tomcat/webapps/* && \
    mkdir -p /usr/local/tomcat/webapps/ROOT && \
    chmod +rx /usr/local/bin/docker-entrypoint.sh && \
    mkdir $DHIS2_HOME && \
    mkdir $DATA_DIR && \
    addgroup --system tomcat && \
    addgroup root tomcat && \
    useradd --shell /bin/bash --uid 101 --gid tomcat tomcat

RUN apt-get update
RUN echo 'You can disregard the warning in noninteractive installations:' \
         '"debconf: delaying package configuration, since apt-utils is not installed"'
RUN apt-get install --no-install-recommends -y \
        unzip curl postgresql-client fonts-dejavu fontconfig util-linux

COPY dhis.war /usr/local/tomcat/webapps/ROOT.war
COPY dhis2-home-files /dhis2-home-files

CMD ["catalina.sh", "run"]
