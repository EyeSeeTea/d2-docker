FROM alpine

RUN mkdir /data/
RUN mkdir /data/db
COPY db/* /data/db/
COPY run.sh /usr/local/bin/

COPY apps/ /data/apps

CMD ["sh", "/usr/local/bin/run.sh"]
