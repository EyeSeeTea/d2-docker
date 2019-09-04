## Requirements

-   Python >= 3.5 (with python3-distutils)
-   Docker >= 18
-   Docker compose >= 1.17

## Usage

### Start a DHIS2 instance

Start a new container from a _dhis2-data_ base image:

```
$ bin/d2-docker start eyeseetea/dhis2-data:2.30-sierra
```

Notes:

-   A d2-docker instance is composed of 4 containers: `dhis2-data` (db + apps), `dhis2-core` (tomcat + war), `postgis` (postgres with postgis support) and `nginx`.
-   By default, the image `dhis2-core` from the same organisation will be used, keeping the first part of the tag (using `-` as separator). For example: `eyeseetea/dhis2-data:2.30-sierra` will use core `eyeseetea/dhis2-core:2.30`. If you need a custom image to be used, pass the option `--core-image eyeseetea/dhis2-core:2.30-custom`.
-   Once started, you can connect to the DHIS2 instance (`http://localhost:PORT`) where _PORT_ is the first available port starting from 8080. You can run many images at the same time, but not the same image more than once. You can specify the port with option `-p PORT`.
-   Use option `--pull` to overwrite the local images with the images in the hub. Use option ``--detach` to start containers in the background.
-   Use option `-k`/`--keep-containers` to re-use existing containers, so data from the previous run will be kept.
-   Use option `--run-sql` to run SQL (.sql or .sql.gz) files after the DB has been initialized.
-   Use option `--run-scripts` to run shell scripts (.sh) from a directory within the `dhis2-core` container. By default, a script is run **after** postgres starts (`host=db`, `port=5432`) but **before** Tomcat starts; if its filename starts with prefix "post", it will be run **after** Tomcat is available. `curl` and typical shell tools are available on that Alpine Linux environment. Note that the Dhis2 endpoint is always `http://localhost:8080`, regardless of the public port that the instance is exposed to. Of course, this endpoint is only available only on post-scripts.

### Show logs for running containers

Check logs of a running container:

```
$ bin/d2-docker logs -f eyeseetea/dhis2-data:2.30-sierra
```

_If only one d2-docker container is active, you can omit the image name._

### Commit & push an image

This will create a new _dhis2-data_ image from the current data (SQL dump and apps) in running d2-docker containers:

```
$ bin/d2-docker commit eyeseetea/dhis2-data:2.30-sierra
```

Now you can upload images to hub.docker using the command _push_:

```
$ bin/d2-docker push eyeseetea/dhis2-data:2.30-sierra
```

_If only one d2-docker container is active, you can omit the image name._

### Stop a DHIS2 container instance

Stop running containers:

```
$ bin/d2-docker stop eyeseetea/dhis2-data:2.30-sierra
```

_If only one d2-docker container is active, you can omit the image name._

### Export a DHIS2 container instance to a file

You can export all the images needed by d2-docker to a single file, ready to distribute.

Note that you must commit any changes first, since this will export images, not containers.

```
$ bin/d2-docker export -i eyeseetea/dhis2-data:2.30-sierra dhis2-sierra.tgz
```

Now you can copy this file to any other machine, which may now use commands _import FILE_ and _start FILE_.

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

On the first run, the images will been created, but you can either run this command again or the standard `start DHIS2_DATA_IMAGE_NAME`.

### Copy Docker images to/from local directories

You can use a Docker image or a data directory (db + apps) as source, that will create a new Docker image _eyeseetea/dhis2-data:2.30-sierra2_ and a `sierra-data/` directory:

```
$ bin/d2-docker copy eyeseetea/dhis2-data:2.30-sierra eyeseetea/dhis2-data:2.30-sierra2 sierra-data

$ docker image ls | grep 2.30-sierra2
eyeseetea/dhis2-data      2.30-sierra2         930aced0d915        1 minutes ago      106MB
$ ls sierra-data/
apps  db.sql.gz
```

Alternatively, you can use a data directory (db + apps) as source and create Docker images from it:

```
$ bin/d2-docker copy sierra-data eyeseetea/dhis2-data:2.30-sierra3 eyeseetea/dhis2-data:2.30-sierra4
[...]
$ docker image ls | grep "2.30-sierra\(3\|4\)"
eyeseetea/dhis2-data      2.30-sierra3         930aced0d915        1 minutes ago      106MB
eyeseetea/dhis2-data      2.30-sierra4         d3a374301234        1 minutes ago      106MB
```

### List all local d2-docker data images

Lists _dhis2-data_ images present in the local repository and the container status:

```
$ bin/d2-docker.py list
eyeseetea/dhis2-data:2.30-sierra RUNNING[port=8080]
eyeseetea/dhis2-data:2.30-vietnam STOPPED
eyeseetea/dhis2-data:2.30-cambodia STOPPED
```

### Run SQL file in container

Run SQL in a running Dhis2 instance. Note that some changes won't be visible depending on the cache policies of the instance.

```
$ echo "update dashboard set name = 'Antenatal Care Name' where uid = 'nghVC4wtyzi'" > set-name.sql

$ bin/d2-docker.py run-sql -i eyeseetea/dhis2-data:2.30-sierra set-name.sql
[d2-docker:INFO] Run SQL file set-name.sql for image eyeseetea/dhis2-data:2.30-sierra
UPDATE 1
```

## Docker instances

In addition to the _dhis2-data_ image, `d2-docker` needs those base images to work:

-   [eyeseetea/postgis:10-alpine](https://hub.docker.com/r/eyeseetea/eyeseetea/postgis)
-   [eyeseetea/dhis2-core:2.30](https://hub.docker.com/r/eyeseetea/dhis2-core)
-   [jwilder/nginx-proxy:alpine](https://hub.docker.com/r/jwilder/nginx-proxy)

The folder `images/` contains the source code for those Docker images. Should you ever need to modify those base images, build them and push to the hub repository:

```
$ cd images/dhis2-core
$ cp /path/to/dhis.war .
$ docker build . --tag="eyeseetea/dhis2-core:2.30"
$ docker push eyeseetea/dhis2-core:2.30
```

```
$ cd images/postgis
$ docker build . --tag="eyeseetea/postgis:10-alpine"
$ docker push "eyeseetea/postgis:10-alpine"
```

This folder also contains the source code for `dhis2-data` docker image, which is used internally by the scripts to create new images (in a commit, for example). You may also need to modify base images and push them:

```
$ cd images/dhis2-data
$ cp /path/to/dhis2-db-for-vietnam.sql.gz db.sql.gz
$ docker build . --tag="eyeseetea/dhis2-data:2.30-vietnam"
$ docker push "eyeseetea/dhis2-data:2.30-vietnam"
```
