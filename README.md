## Usage

### Start a container

Start a new container from a _dhis2-db_ image:

```
$ bin/d2-docker start eyeseetea/dhis2-db:2.30-sierra
```

This will start 3 containers (dhis2-core, postgres and nginx). Now you can connect to the DHIS2 instance (`http://localhost:PORT`) where _PORT_ is the first available port starting from 8080. You can run many images at the same time (but not the same image more than once).

Use option `--pull` to overwrite the local images with the images in the hub. Use option ``--detach` to start containers in the background.

### Show logs for a container

Check logs of a running container:

```
$ bin/d2-docker logs eyeseetea/dhis2-db:2.30-sierra
```

_If only one d2-docker container is active, you can omit the image name._

### Stop a container

Stop a running container:

```
$ bin/d2-docker stop eyeseetea/dhis2-db:2.30-sierra
```

_If only one d2-docker container is active, you can omit the image name._
