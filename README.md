## Requirements

-   Python >= 3.5 (with python3-distutils)
-   Docker >= 18
-   Docker compose >= 1.17

## Install

\$ sudo python3 setup.py install

## Usage

### Start a DHIS2 instance

Start a new container from a _dhis2-data_ base image:

```
$ d2-docker start eyeseetea/dhis2-data:2.30-sierra
```

Notes:

-   A d2-docker instance is composed of 4 containers: `dhis2-data` (database + apps), `dhis2-core` (tomcat + dhis.war), `postgis` (postgres with postgis support) and `nginx` (web server).
-   By default, the image `dhis2-core` from the same organisation will be used, keeping the first part of the tag (using `-` as separator). For example: `eyeseetea/dhis2-data:2.30-sierra` will use core `eyeseetea/dhis2-core:2.30`. If you need a custom image to be used, pass the option `--core-image eyeseetea/dhis2-core:2.30-custom`.
-   Once started, you can connect to the DHIS2 instance (`http://localhost:PORT`) where _PORT_ is the first available port starting from 8080. You can run many images at the same time, but not the same image more than once. You can specify the port with option `-p PORT`.
-   Use option `--pull` to overwrite the local images with the images in the hub. Use option `--detach` to run containers in the background.
-   Use option `-k`/`--keep-containers` to re-use existing containers, so data from the previous run will be kept.
-   Use option `--run-sql=DIRECTORY` to run SQL files (.sql or .sql.gz) after the DB has been initialized.
-   Use option `--run-scripts=DIRECTORY` to run shell scripts (.sh) from a directory within the `dhis2-core` container. By default, a script is run **after** postgres starts (`host=db`, `port=5432`) but **before** Tomcat starts; if its filename starts with prefix "post", it will be run **after** Tomcat is available. `curl` and typical shell tools are available on that Alpine Linux environment. Note that the Dhis2 endpoint is always `http://localhost:8080`, regardless of the public port that the instance is exposed to. Of course, this endpoint is only available for post-scripts.

### Show logs for running containers

Check logs of a running container:

```
$ d2-docker logs -f eyeseetea/dhis2-data:2.30-sierra
```

_If only one d2-docker container is active, you can omit the image name._

### Commit & push an image

This will update the image from the current container (SQL dump and apps):

```
$ d2-docker commit
```

You can also create a new _dhis2-data_ image from the running d2-docker containers:

```
$ d2-docker commit eyeseetea/dhis2-data:2.30-sierra-new
```

Now you can upload images to hub.docker using the command _push_:

```
$ d2-docker push eyeseetea/dhis2-data:2.30-sierra
```

### Stop a DHIS2 container instance

Stop running containers:

```
$ d2-docker stop eyeseetea/dhis2-data:2.30-sierra
```

_If only one d2-docker container is active, you can omit the image name._

### Export a DHIS2 container instance to a file

You can export all the images needed by d2-docker to a single file, ready to distribute.

Note that you must commit any changes first, since this will export images, not containers.

```
$ d2-docker export -i eyeseetea/dhis2-data:2.30-sierra dhis2-sierra.tgz
```

Now you can copy this file to any other machine, which may now use commands _import FILE_ and _start FILE_.

_If only one d2-docker container is active, you can omit the image name._

### Import a DHIS2 instance from an exported file

Use the output file from command _export_ to create all d2-docker images required:

```
$ d2-docker import dhis2-sierra.tgz
```

### Start DHIS2 instance from an exported file

You can use the same _start_ command, passing the file instead of the image name. `d2-docker` will then import the images of the file and automatically start the DHIS2 instance it contains.

```
$ d2-docker start dhis2-sierra.tgz
```

On the first run, the images will been created, but you can either run this command again or the standard `start DHIS2_DATA_IMAGE_NAME`.

### Copy Docker images to/from local directories

You can use a Docker image or a data directory (db + apps) as source, that will create a new Docker image _eyeseetea/dhis2-data:2.30-sierra2_ and a `sierra-data/` directory:

```
$ d2-docker copy eyeseetea/dhis2-data:2.30-sierra eyeseetea/dhis2-data:2.30-sierra2 sierra-data

$ docker image ls | grep 2.30-sierra2
eyeseetea/dhis2-data      2.30-sierra2         930aced0d915        1 minutes ago      106MB
$ ls sierra-data/
apps  db.sql.gz
```

Alternatively, you can use a data directory (db + apps) as source and create Docker images from it:

```
$ d2-docker copy sierra-data eyeseetea/dhis2-data:2.30-sierra3 eyeseetea/dhis2-data:2.30-sierra4
[...]
$ docker image ls | grep "2.30-sierra\(3\|4\)"
eyeseetea/dhis2-data      2.30-sierra3         930aced0d915        1 minutes ago      106MB
eyeseetea/dhis2-data      2.30-sierra4         d3a374301234        1 minutes ago      106MB
```

### List all local d2-docker data images

Lists _dhis2-data_ images present in the local repository and the container status:

```
$ d2-docker.py list
eyeseetea/dhis2-data:2.30-sierra RUNNING[port=8080]
eyeseetea/dhis2-data:2.30-vietnam STOPPED
eyeseetea/dhis2-data:2.30-cambodia STOPPED
```

### Run SQL file in container

Run SQL in a running Dhis2 instance. Note that some changes won't be visible depending on the cache policies of the instance.

```
$ echo "update dashboard set name = 'Antenatal Care Name' where uid = 'nghVC4wtyzi'" > set-name.sql

$ d2-docker.py run-sql -i eyeseetea/dhis2-data:2.30-sierra set-name.sql
[d2-docker:INFO] Run SQL file set-name.sql for image eyeseetea/dhis2-data:2.30-sierra
UPDATE 1
```

## Docker instances

In addition to the _dhis2-data_ image, `d2-docker` needs those base images to work:

-   [mdillon/postgis:10-alpine](https://hub.docker.com/r/mdillon/postgis/)
-   [jwilder/nginx-proxy:alpine](https://hub.docker.com/r/jwilder/nginx-proxy)
-   [eyeseetea/dhis2-core:2.30](https://hub.docker.com/r/eyeseetea/dhis2-core)

The folder `images/` contains the source code for our custom Docker images. Should you ever need to modify those base images, build them and push to the hub repository:

```
$ cd images/dhis2-core
$ cp /path/to/new/dhis.war .
$ docker build . --tag="eyeseetea/dhis2-core:2.30"
$ docker push eyeseetea/dhis2-core:2.30
```

This folder also contains the source code for `dhis2-data` docker image, which is used internally by the scripts to create new images (in a commit, for example). You may also need to modify base images and push them:

```
$ cd images/dhis2-data
$ cp /path/to/dhis2-db-for-vietnam.sql.gz db.sql.gz
$ docker build . --tag="eyeseetea/dhis2-data:2.30-vietnam"
$ docker push "eyeseetea/dhis2-data:2.30-vietnam"
```

However, you tipically create new `dhis2-data` images by using the the `d2-docker copy` command.

## Clean-up

Docker infrastructure (images, networks, containers, volumes) take up a lot of space. Some command to clean-up:

Remove all local volumes not used by at least one container:

```
$ docker container prune
```

Remove all stopped containers:

```
$ docker container prune
```

Remove all dangling images (the temporal images that have `<none>` on its name/tag):

```
$ docker image prune
```

**WARNING:: Dangerous operation**: Delete all stopped containers, networks, volumes, images and cache. Note, that any `dhis2-data` image not pushed to the repository, will be also deleted (as it's not kept as an active container):

```
$ docker system prune -a --volumes
```
