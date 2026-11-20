FROM alpine:3.24

RUN mkdir /data/
RUN mkdir /data/db
COPY db/ /data/db/
COPY run.sh /usr/local/bin/

COPY apps/ /data/apps
COPY document/ /data/document
COPY dataValue/ /data/dataValue
COPY pushAnalysis/ /data/pushAnalysis
COPY messageAttachment/ /data/messageAttachment
COPY userAvatar/ /data/userAvatar
COPY organisationUnit/ /data/organisationUnit
COPY icon/ /data/icon
COPY jobData/ /data/jobData

CMD ["sh", "/usr/local/bin/run.sh"]
