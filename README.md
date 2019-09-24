## Requirements

-   Python >= 3.5 (with setuptools).
-   Docker >= 18
-   Docker compose >= 1.17

In Ubuntu 18.04:

```
\$ sudo apt install docker.io docker-compose python3 python3-setuptools
```

## Install

```

\$ sudo python3 setup.py install

```

## Usage

### Setup core

First we need to create a core image for a specific version of DHIS2 we want to use (check available versions at [releases.dhis2.org](https://releases.dhis2.org/)):

```

\$ d2-docker create core eyeseetea/dhis2-core:2.30 --version=2.30

```

Alternatively, you may directly specify the WAR file:

```

\$ d2-docker create core eyeseetea/dhis2-core:2.30 --war=dhis.war

```

### Create a base DHIS2 data image

Create a dhis2-data image from a .sql.gz SQL file and the apps directory to include:

```

\$ d2-docker create data eyeseetea/dhis2-data:2.30-sierra --sql=sierra-db.sql.gz [--apps-dir=path/to/apps]

```

### Start a DHIS2 instance

Start a new container from a _dhis2-data_ base image:

```

\$ d2-docker start eyeseetea/dhis2-data:2.30-sierra

```

Some notes:

-   A d2-docker instance is composed of 4 containers: `dhis2-data` (database + apps), `dhis2-core` (tomcat + dhis.war), `postgis` (postgres with postgis support) and `nginx` (web server).
-   By default, the image `dhis2-core` from the same organisation will be used, keeping the first part of the tag (using `-` as separator). For example: `eyeseetea/dhis2-data:2.30-sierra` will use core `eyeseetea/dhis2-core:2.30`. If you need a custom image to be used, use `--core-image= eyeseetea/dhis2-core:2.30-custom`.
-   Once started, you can connect to the DHIS2 instance (`http://localhost:PORT`) where _PORT_ is the first available port starting from 8080. You can run many images at the same time, but not the same image more than once. You can specify the port with option `-p PORT`.
-   Use option `--pull` to overwrite the local images with the images in the hub.
-   Use option `--detach` to run containers in the background.
-   Use option `-k`/`--keep-containers` to re-use existing containers, so data from the previous run will be kept.
-   Use option `--run-sql=DIRECTORY` to run SQL files (.sql, .sql.gz or .dump files) after the DB has been initialized.
-   Use option `--run-scripts=DIRECTORY` to run shell scripts (.sh) from a directory within the `dhis2-core` container. By default, a script is run **after** postgres starts (`host=db`, `port=5432`) but **before** Tomcat starts; if its filename starts with prefix "post", it will be run **after** Tomcat is available. `curl` and typical shell tools are available on that Alpine Linux environment. Note that the Dhis2 endpoint is always `http://localhost:8080`, regardless of the public port that the instance is exposed to. Of course, this endpoint is only available for post-scripts.

### Show logs for running containers

Check logs of a running container:

```

\$ d2-docker logs -f eyeseetea/dhis2-data:2.30-sierra

```

_If only one d2-docker container is active, you can omit the image name._

### Commit & push an image

This will update the image from the current container (SQL dump and apps):

```

\$ d2-docker commit

```

You can also create a new _dhis2-data_ image from the running d2-docker containers:

```

\$ d2-docker commit eyeseetea/dhis2-data:2.30-sierra-new

```

Now you can upload images to hub.docker using the command _push_:

```

\$ d2-docker push eyeseetea/dhis2-data:2.30-sierra

```

### Stop a DHIS2 container instance

Stop running containers:

```

\$ d2-docker stop eyeseetea/dhis2-data:2.30-sierra

```

_If only one d2-docker container is active, you can omit the image name._

### Export a DHIS2 container instance to a file

You can export all the images needed by d2-docker to a single file, ready to distribute.

Note that you must commit any changes first, since this will export images, not containers.

```

\$ d2-docker export -i eyeseetea/dhis2-data:2.30-sierra dhis2-sierra.tgz

```

Now you can copy this file to any other machine, which may now use commands _import FILE_ and _start FILE_.

_If only one d2-docker container is active, you can omit the image name._

### Import a DHIS2 instance from an exported file

Use the output file from command _export_ to create all d2-docker images required:

```

\$ d2-docker import dhis2-sierra.tgz

```

### Start DHIS2 instance from an exported file

You can use the same _start_ command, passing the file instead of the image name. `d2-docker` will then import the images of the file and automatically start the DHIS2 instance it contains.

```

\$ d2-docker start dhis2-sierra.tgz

```

On the first run, the images will been created, but you can either run this command again or the standard `start DHIS2_DATA_IMAGE_NAME`.

### Copy Docker images to/from local directories

You can use a Docker image or a data directory (db + apps) as source, that will create a new Docker image _eyeseetea/dhis2-data:2.30-sierra2_ and a `sierra-data/` directory:

```

\$ d2-docker copy eyeseetea/dhis2-data:2.30-sierra eyeseetea/dhis2-data:2.30-sierra2 sierra-data

$ docker image ls | grep 2.30-sierra2
eyeseetea/dhis2-data      2.30-sierra2         930aced0d915        1 minutes ago      106MB
$ ls sierra-data/
apps db.sql.gz

```

Alternatively, you can use a data directory (db + apps) as source and create Docker images from it:

```

$ d2-docker copy sierra-data eyeseetea/dhis2-data:2.30-sierra3 eyeseetea/dhis2-data:2.30-sierra4
[...]
$ docker image ls | grep "2.30-sierra\(3\|4\)"
eyeseetea/dhis2-data 2.30-sierra3 930aced0d915 1 minutes ago 106MB
eyeseetea/dhis2-data 2.30-sierra4 d3a374301234 1 minutes ago 106MB

```

### List all local d2-docker data images

Lists _dhis2-data_ images present in the local repository and the container status:

```

\$ d2-docker.py list
eyeseetea/dhis2-data:2.30-sierra RUNNING[port=8080]
eyeseetea/dhis2-data:2.30-vietnam STOPPED
eyeseetea/dhis2-data:2.30-cambodia STOPPED

```

### Run SQL file in container

Run a SQL file or open an interactive postgres session in a running Dhis2 instance:

```

\$ d2-docker.py run-sql [-i eyeseetea/dhis2-data:2.30-sierra] some-query.sql

```

## Clean-up

Docker infrastructure (images, networks, containers, volumes) takes up a lot of hard-disk space.

Remove all local volumes not used by at least one container:

```

\$ docker volume prune

```

Remove all stopped containers:

```

\$ docker container prune

```

Remove all dangling images (the temporal images that have `<none>` on its name/tag):

```

\$ docker image prune

```

**WARNING: Dangerous operation** Delete all stopped containers, networks, volumes, images and cache. Note, that any `dhis2-data` image still not pushed to the repository, will be also deleted whether the instance is running or nor (as it's not kept as an active container):

```

\$ docker system prune -a --volumes

```

```

```
