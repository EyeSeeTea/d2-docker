FROM alpine

RUN mkdir /data/
COPY db.sql.gz /data/
COPY run.sh /usr/local/bin/

COPY apps/ /data/apps

CMD ["sh", "/usr/local/bin/run.sh"]
