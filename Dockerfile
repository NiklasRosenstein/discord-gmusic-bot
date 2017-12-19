FROM heroku/heroku:16-build

WORKDIR /app
COPY . ./

ENV BUILDPACK_URL=https://github.com/nodepy/nodepy-buildpack
ENV BUILD_DIR=/app
ENV CACHE_DIR=/app-cache
ENV ENV_DIR=/app-env

RUN apt-get update && apt-get install -y libopus-dev libssl-dev ffmpeg
RUN /bin/bash -c 'git clone $BUILDPACK_URL /buildpack'
RUN /bin/bash -c '/buildpack/bin/compile $BUILD_DIR $CACHE_DIR $ENV_DIR'

ENV PATH="/app/.heroku/python/bin:.nodepy/bin:${PATH}"
