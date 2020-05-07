# nginx:alpine contains NGINX_VERSION environment variable, like so:
ARG NGINX_VERSION=1.17.6
ARG KUBECTL_VERSION=v1.18.1
ARG NGINX_INFLUXDB_MODULE_VERSION=5b09391cb7b9a889687c0aa67964c06a2d933e8b

FROM nginx:${NGINX_VERSION}-alpine AS builder
LABEL stage=intermediate

# required after the FROM statement to pass through
ARG NGINX_VERSION
ARG KUBECTL_VERSION
ARG NGINX_INFLUXDB_MODULE_VERSION

# Download sources
RUN wget "http://nginx.org/download/nginx-${NGINX_VERSION}.tar.gz"

# For latest build deps, see https://github.com/nginxinc/docker-nginx/blob/master/mainline/alpine/Dockerfile
RUN apk add --no-cache --virtual .build-deps \
  gcc \
  libc-dev \
  make \
  openssl-dev \
  pcre-dev \
  zlib-dev \
  linux-headers \
  curl \
  gnupg \
  libxslt-dev \
  gd-dev \
  geoip-dev \
  git

RUN git clone http://github.com/influxdata/nginx-influxdb-module.git
RUN (cd nginx-influxdb-module && git reset --hard $NGINX_INFLUXDB_MODULE_VERSION)

# Reuse same cli arguments as the nginx:alpine image used to build
RUN CONFARGS=$(nginx -V 2>&1 | sed -n -e 's/^.*arguments: //p') \
  tar -zxC . -f nginx-${NGINX_VERSION}.tar.gz && \
  MODULEDIR="$(pwd)/nginx-influxdb-module" && \
  cd nginx-${NGINX_VERSION} && \
  ./configure --with-compat $CONFARGS --add-dynamic-module=$MODULEDIR && \
  make && make install

# grab binary from github releases
RUN curl -LO https://storage.googleapis.com/kubernetes-release/release/$KUBECTL_VERSION/bin/linux/amd64/kubectl

# mark as executable
RUN chmod +x ./kubectl

FROM nginx:${NGINX_VERSION}-alpine

# Extract the dynamic module influxdb from the builder image
COPY --from=builder /usr/local/nginx/modules/ngx_http_influxdb_module.so /usr/local/nginx/modules/ngx_http_influxdb_module.so
COPY --from=builder ./kubectl /usr/local/bin/kubectl
