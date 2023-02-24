FROM nginx:alpine

ARG PUBLIC_BASE_URL=https://my-epic-lab.io
ARG GCP_PROJECT_NAME

COPY ./default.conf.template /etc/nginx/conf.d/default.conf.template
COPY ./nginx.conf /etc/nginx/nginx.conf

RUN cat /etc/nginx/conf.d/default.conf.template \
    | sed "s|__BUILD_ARG_PUBLIC_BASE_URL__|$PUBLIC_BASE_URL|g" \
    | sed "s|__BUILD_ARG_GCP_PROJECT_NAME__|$GCP_PROJECT_NAME|g" \
    > /etc/nginx/conf.d/default.conf
