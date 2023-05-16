## Requirements

- Operating System: GNU/Linux or Windows 10.
- Python >= 3.5 (with setuptools)
- Docker >= 18
- Docker compose >= 1.17
- RAM memory: At least 4Gb for instance, preferrably 8Gb.

On Ubuntu 18.04:

```
$ sudo apt install docker.io docker-compose python3 python3-setuptools
```

On Windows 10:

- Install Python: https://www.python.org/downloads
- Install Docker Desktop: https://docs.docker.com/docker-for-windows/install
- Activate WSL2 (this may require to install some other dependencies):
  ![image (20)](https://user-images.githubusercontent.com/6850223/138077958-3fb8a9a8-e829-495a-9b25-f0e347e411d1.png)

## Install

On GNU/Linux:

```
$ sudo python3 setup.py install
```

If you are behind a proxy you must execute the following line to make proxy running installing pip packages:
```
sudo -E python3 setup.py install
```

For Windows, open a terminal as an Administrator and run:

```
$ python setup.py install
```

## Usage

### Setup core

First we need to create a core image for a specific version of DHIS2 we want to use (check available versions at [releases.dhis2.org](https://releases.dhis2.org/)):

```
$ d2-docker create core docker.eyeseetea.com/eyeseetea/dhis2-core:2.37.9 --version=2.37.9
```

Alternatively, you may directly specify the WAR file:

```
$ d2-docker create core docker.eyeseetea.com/eyeseetea/dhis2-core:2.37.9 --war=dhis.war
```

You can add configuration files to folder DHIS2_HOME. A typical example is to add the GEE (Google Earth Engine) credentials:

```
$ d2-docker create core docker.eyeseetea.com/eyeseetea/dhis2-core:2.37.9 --war=dhis.war --dhis2-home=/tmp/dhis-google-auth.json
```

### Create a base DHIS2 data image

Create a dhis2-data image from a .sql.gz SQL file and the apps and documents (or datavalue fileresources) directory to include:

```
$ d2-docker create data docker.eyeseetea.com/eyeseetea/dhis2-data:2.37.9-sierra --sql=sierra-db.sql.gz [--apps-dir=path/to/apps] [--documents-dir=path/to/document] [--datavalues-dir=path/to/dataValue]
```

### Start a DHIS2 instance

Start a new container from a _dhis2-data_ base image:

```
$ d2-docker start docker.eyeseetea.com/eyeseetea/dhis2-data:2.37.9-sierra
```

Some notes:

- A d2-docker instance is composed of 4 containers: `dhis2-data` (database + apps), `dhis2-core` (tomcat + dhis.war), `postgis` (postgres with postgis support) and `nginx` (web server).
- By default, the image `dhis2-core` from the same organisation will be used, keeping the first part of the tag (using `-` as separator). For example: `eyeseetea/dhis2-data:2.30-sierra` will use core `eyeseetea/dhis2-core:2.30`. If you need a custom image to be used, use `--core-image= eyeseetea/dhis2-core:2.30-custom`.
- Once started, you can connect to the DHIS2 instance (`http://localhost:PORT`) where _PORT_ is the first available port starting from 8080. You can run many images at the same time, but not the same image more than once. You can specify the port with option `-p PORT`.
- Use option `--pull` to overwrite the local images with the images in the hub.
- Use option `--detach` to run the container in the background.
- Use option `--deploy-path` to run the container with a deploy path namespace (i.e: `--deploy-path=dhis2` serves `http://localhost:8080/dhis2`)
- Use option `-k`/`--keep-containers` to re-use existing docker containers, so data from the previous run will be kept.
- Use option `-auth` to pass the instance authentication (`USER:PASS`). It will be used to call post-tomcat scripts.
- Use option `--run-sql=DIRECTORY` to run SQL files (.sql, .sql.gz or .dump files) after the DB has been initialized.
- Use option `--run-scripts=DIRECTORY` to run shell scripts (.sh) from a directory within the `dhis2-core` container. By default, a script is run **after** postgres starts (`host=db`, `port=5432`) but **before** Tomcat starts; if its filename starts with prefix "post", it will be run **after** Tomcat is available. `curl` and typical shell tools are available on that Alpine Linux environment. Note that the Dhis2 endpoint is always `http://localhost:8080/${deployPath}`, regardless of the public port that the instance is exposed to.
- Use option `--java-opts="JAVA_OPTS"` to override the default JAVA_OPTS for the Tomcat process. That's tipically used to set the maximum/initial Heap Memory size (for example: `--java-opts="-Xmx3500m -Xms2500m"`)
- Use option `--postgis-version=13-3.1-alpine` to specify the PostGIS version to use. By default, 10-2.5-alpine is used.

#### Custom DHIS2 dhis.conf

Copy the default [dhis.conf](https://github.com/EyeSeeTea/d2-docker/blob/master/src/d2_docker/config/DHIS2_home/dhis.conf) and use it as a template to create your own configuration. Then pass it to the `start` command:

```
$ d2-docker start --dhis-conf=dhis.conf ...
```

#### Custom Tomcat server.xml

Copy the default [server.xml](https://github.com/EyeSeeTea/d2-docker/blob/master/src/d2_docker/config/server.xml) and use it as a template to create your own configuration. Then pass it to the `start` command:

```
$ d2-docker start --tomcat-server-xml=server-xml.xml ...
```

Note that you should not change the catalina connector port (8080, by default). A typical configuration to use _https_ would look like this:

```
<Server port="8005" shutdown="SHUTDOWN">
    ...
    <Service name="Catalina">
        <Connector
            port="8080"
            protocol="HTTP/1.1"
            proxyPort="443"
            scheme="https"
            secure="true"
            proxyName="some-host.org"
            connectionTimeout="20000"
            URIEncoding="UTF-8"
            relaxedQueryChars='\ { } | [ ]'
            redirectPort="8443"
        />
    ...
/>
```

### Run terminal shell in DHIS2 core container

```
$ d2-docker shell eyeseetea/dhis2-data:2.30-sierra
```

### Show logs for running containers

Check logs of a running container:

```
$ d2-docker logs -f eyeseetea/dhis2-data:2.30-sierra
```

_If only one d2-docker container is active, you can omit the image name._

### Commit & push an image

This will update the image from the current container (SQL dump, apps and documents):

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
$ d2-docker export -i eyeseetea/dhis2-data:2.30-sierra dhis2-sierra
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

### Delete image/containers linked to an instance

```
$ d2-docker rm eyeseetea/dhis2-data:2.30-sierra
```

### Copy Docker images to/from local directories

You can use a Docker image or a data directory (db + apps + documents) as source, that will create a new Docker image _eyeseetea/dhis2-data:2.30-sierra2_ and a `sierra-data/` directory:

```
$ d2-docker copy eyeseetea/dhis2-data:2.30-sierra eyeseetea/dhis2-data:2.30-sierra2 sierra-data

$ docker image ls | grep 2.30-sierra2
eyeseetea/dhis2-data      2.30-sierra2         930aced0d915        1 minutes ago      106MB

$ ls sierra-data/
apps document db.sql.gz
```

Alternatively, you can use a data directory (db + apps + documents) as source and create Docker images from it:

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
$ d2-docker list
eyeseetea/dhis2-data:2.30-sierra RUNNING[port=8080]
eyeseetea/dhis2-data:2.30-vietnam STOPPED
eyeseetea/dhis2-data:2.30-cambodia STOPPED
```

### Run SQL file in container

Run a SQL file or open an interactive postgres session in a running Dhis2 instance:

```
$ d2-docker run-sql [-i eyeseetea/dhis2-data:2.30-sierra] some-query.sql
```

### Dump current database to SQL file in container

```
$ d2-docker run-sql [-i eyeseetea/dhis2-data:2.30-sierra] --dump
```

### Upgrade DHIS2 version

```
$ d2-docker upgrade \
    --from=eyeseetea/dhis2-data:2.30-sierra \
    --to=eyeseetea/dhis2-data:2.32-sierra \
    --migrations=upgrade-sierra/
```

Migration folder `upgrade-sierra` should then contain data to be used in each intermediate upgrade version. Supported migration data:

- DHIS2 war file: `dhis.war` (if not specified, it will be download from the releases page)
- DHIS2 home files: `dhis2-home/`
- Shell scripts (pre-tomcat): `*.sh`
- Shell scripts (post-tomcat): `post-*.sh`
- SQL files: `*.sql`

A full example might look:

```
upgrade-sierra/2.31/dhis.war
upgrade-sierra/2.31/fix-users.sql
upgrade-sierra/2.31/dhis2-home/dhis-google-auth.json
upgrade-sierra/2.31/post-metadata.sh
upgrade-sierra/2.31/some-metadata-used-by-the-script.json

upgrade-sierra/2.32/fix-org-units-geometry.sql
```

## Clean-up

Docker infrastructure (images, networks, containers, volumes) takes up a lot of hard-disk space.

Remove all local volumes not used by at least one container:

```
$ docker volume prune
```

Remove all stopped containers:

```
$ docker container prune
```

Remove all dangling images (the temporal images that have `<none>` on its name/tag):

```
$ docker image prune
```

**WARNING: Dangerous operation** Delete all stopped containers, networks, volumes, images and cache. Note, that any `dhis2-data` image still not pushed to the repository, will be also deleted whether the instance is running or nor (as it's not kept as an active container):

```
$ docker system prune -a --volumes
```

## Development

### Run d2-docker from sources

```
$ ./d2-docker-dev.sh
```

### Dockerized d2-docker (d2-container)

Create a dockerized d2-docker:

```
$ bash build-docker-container.sh
```

### API Server

Start Flask server in development mode:

```
$ FLASK_ENV=development flask run
```

Usage examples:

```
$ curl http://localhost:5000/version

$ curl  -H "Content-Type: application/json" -sS http://localhost:5000/instances/start -X POST \
    -d '{"image": "docker.eyeseetea.com/samaritans/dhis2-data:2.36.8-sp-ip-training", "port": 8080, "detach": true}'
```

Currently, there are no API docs nor params validations. For each command `src/d2_docker/commands/COMMAND.py`, check function `setup` to see the supported parameters.

The API server provides a proxy to Harbor to bypass CORS issues. Configure first the harbor authentication file:

```
$ cp flaskenv.secret.template flaskenv.secret
$ # Edit flaskenv.secret
$ mkdir -p ~/.config/d2-docker/
$ cp flaskenv.secret ~/.config/d2-docker/

$ curl -sS 'http://localhost:5000/harbor/https://docker.eyeseetea.com/api/v2.0/quotas/1' | jq
```
