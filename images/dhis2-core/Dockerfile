FROM tomcat:8.5.34-jre8-alpine

RUN apk add --update curl && rm -rf /var/cache/apk/*

RUN rm -rf /usr/local/tomcat/webapps/*
COPY ./dhis.war /usr/local/tomcat/webapps/ROOT.war
COPY ./start.sh /usr/local/bin/
ENV DHIS2_HOME=/DHIS2_home

CMD ["sh", "/usr/local/bin/start.sh"]
