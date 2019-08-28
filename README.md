## Usage

### Start a DHIS2 instance

Start a new container from a _dhis2-db_ image:

```
$ bin/d2-docker start eyeseetea/dhis2-db:2.30-sierra
```

This will start 3 containers (dhis2-core, postgres and nginx). Now you can connect to the DHIS2 instance (`http://localhost:PORT`) where _PORT_ is the first available port starting from 8080. You can run many images at the same time, but not the same image more than once.

Use option `--pull` to overwrite the local images with the images in the hub. Use option ``--detach` to start containers in the background.

### Show logs for running containers

Check logs of a running container:

```
$ bin/d2-docker logs eyeseetea/dhis2-db:2.30-sierra
```

_If only one d2-docker container is active, you can omit the image name._

### Commit & push an existing DHIS2 instance

This will create a new _dhis2-db_ image from the current data (SQL dump and apps) in d2-docker containers:

```
$ bin/d2-docker commit eyeseetea/dhis2-db:2.30-sierra
```

Now you can upload images to hub.docker using the command _push_:

```
$ bin/d2-docker push eyeseetea/dhis2-db:2.30-sierra
```

_If only one d2-docker container is active, you can omit the image name._

### Stop a DHIS2 instance

Stop running containers:

```
$ bin/d2-docker stop eyeseetea/dhis2-db:2.30-sierra
```

_If only one d2-docker container is active, you can omit the image name._

### Export a DHIS2 instance to a file

You can export all the images needed by d2-docker to a single file.

Note that you must commit any changes first, since this will export images, not containers.

```
$ bin/d2-docker export -i eyeseetea/dhis2-db:2.30-sierra dhis2-sierra.tgz
```

Now you can send distribute this file, which may be used by commands _import_ and _start_

_If only one d2-docker container is active, you can omit the image name._

### Import a DHIS2 instance from an exported file

Use the output file from command _export_ to create all d2-docker images required:

```
$ bin/d2-docker import dhis2-sierra.tgz
```

### Start DHIS2 instance from an exported file

You can use the same _start_ command, passing the file instead of the image name. `d2-docker` will then import the images of the file and automatically start the DHIS2 instance it contains.

```
$ bin/d2-docker start dhis2-sierra.tgz
```

On the first run, the images have been created, you can either run this command or the standard `start DHIS2_DB_IMAGE_NAME`.

### Copy Docker images to/from local directories

You can use a Docker image or a data directory (db + apps) as source, that will create a new Docker image _eyeseetea/dhis2-db:2.30-sierra2_ and a `sierra-data/` directory:

```
$ bin/d2-docker copy eyeseetea/dhis2-db:2.30-sierra eyeseetea/dhis2-db:2.30-sierra2 sierra-data
[...]
$ docker image ls | grep 2.30-sierra2
tokland/dhis2-db      2.30-sierra2         930aced0d915        1 minutes ago      106MB
$ ls sierra-data/
apps  db.sql.gz
```

Alternatively, you can use a data directory (db + apps) as source and create Docker images from it:

```
$ bin/d2-docker copy sierra-data eyeseetea/dhis2-db:2.30-sierra3 eyeseetea/dhis2-db:2.30-sierra4
[...]
$ docker image ls | grep "2.30-sierra\(3\|4\)"
tokland/dhis2-db      2.30-sierra3         930aced0d915        1 minutes ago      106MB
tokland/dhis2-db      2.30-sierra4         930aced0d915        1 minutes ago      106MB
```

### List all local Docker images for d2-docker

Lists _dhis2-db_ images present in the local repository:

```
$ docker image ls | grep dhis2-db
tokland/dhis2-db      2.30-sierra          24c0f8ab01e3        25 minutes ago      83.5MB
tokland/dhis2-db      2.30-sierra2         930aced0d915        About an hour ago   106MB
```