FROM tomcat:9.0.20-jre8-alpine

ENV DHIS2_HOME=/DHIS2_home

COPY docker-entrypoint.sh /usr/local/bin/

RUN rm -rf /usr/local/tomcat/webapps/* && \
    mkdir /usr/local/tomcat/webapps/ROOT && \
    chmod +rx /usr/local/bin/docker-entrypoint.sh && \
    mkdir $DHIS2_HOME && \
    addgroup -S tomcat && \
    addgroup root tomcat && \
    adduser -S -D -G tomcat tomcat

RUN apk add --update --no-cache bash su-exec curl postgresql-client
RUN apk add --no-cache ttf-dejavu
COPY dhis.war /usr/local/tomcat/webapps/ROOT.war
COPY dhis2-home-files /dhis2-home-files


ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

CMD ["catalina.sh", "run"]
