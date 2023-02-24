# Epic lab :: proxy

We recommend using an NGINX reverse proxy for accessing VMs. This part of the repo provides tools to assist in that.

## Docker image

Found in this folder is an image to use for running an NGINX-based container on a dedicated GCE VM. It can probably run
in other services such as Cloud Run, perhaps with some adjustments.

The image takes build-time arguments:
1. `GCP_PROJECT_NAME` (required): the name of the GCP project (used for internal DNS resolution), e.g. `epic-lab-123456`
2. `PUBLIC_BASE_URL` (optional): the base URL for this service, e.g. `https://my-epic-lab.io`

Building the container image can be done using a command such as this:
```shell
sudo docker build . \
  --tag proxy \
  --build-arg GCP_PROJECT_NAME=epic-lab-123456 \
  --build-arg PUBLIC_BASE_URL=https://my-epic-lab.io
```

Running the container image can be done using a command such as this:
```shell
sudo docker run \
  --detach \
  --name nginx \
  --publish 8000:80 \
  proxy
```

A complete solution for storing the container image, deploying it, and maintaining the running container can be found
in the [cloud setup guide](../cloud_setup.md).
