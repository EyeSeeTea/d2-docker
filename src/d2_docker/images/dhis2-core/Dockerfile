FROM tomcat:9.0.64-jre11-openjdk-slim-bullseye

ENV DHIS2_HOME=/DHIS2_home
ENV DHIS2_CERT=/DHIS2_home/who_pub_cert.cert
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

COPY who_pub_cert.cert $DHIS2_CERT
RUN  chmod +rx $DHIS2_CERT
RUN keytool -importcert -alias who_mail_ichigoout -file $DHIS2_CERT -keystore /usr/local/openjdk-11/lib/security/cacerts -storepass changeit -noprompt


RUN apt-get update
RUN echo 'You can disregard the warning in noninteractive installations:' \
         '"debconf: delaying package configuration, since apt-utils is not installed"'
RUN apt-get install --no-install-recommends -y \
        unzip curl postgresql-client fonts-dejavu fontconfig util-linux

COPY dhis.war /usr/local/tomcat/webapps/ROOT.war
COPY dhis2-home-files /dhis2-home-files

CMD ["catalina.sh", "run"]
