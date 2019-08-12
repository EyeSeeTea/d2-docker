FROM alpine

RUN mkdir /data/
COPY db.sql.gz /data/
COPY run.sh /usr/local/bin/

RUN mkdir -p /data/apps

CMD ["sh", "/usr/local/bin/run.sh"]
