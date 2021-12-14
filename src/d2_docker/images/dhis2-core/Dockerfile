FROM tomcat:9.0.55-jre11-temurin

ENV DHIS2_HOME=/DHIS2_home

COPY docker-entrypoint.sh /usr/local/bin/

RUN rm -rf /usr/local/tomcat/webapps/* && \
    mkdir /usr/local/tomcat/webapps/ROOT && \
    chmod +rx /usr/local/bin/docker-entrypoint.sh && \
    mkdir $DHIS2_HOME && \
    addgroup --system tomcat && \
    addgroup root tomcat && \
    adduser --disabled-password --shell /bin/bash --uid 101 --ingroup tomcat tomcat

RUN apt-get update
RUN apt-get install postgresql-client -y
run apt-get install unzip -y

COPY dhis.war /usr/local/tomcat/webapps/ROOT.war
COPY dhis2-home-files /dhis2-home-files
RUN chmod +x /usr/local/bin/docker-entrypoint.sh


ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

CMD ["catalina.sh", "run"]
