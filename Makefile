
DOCKER_IMAGE_NAME = discord-gmusic-bot
DOCKER_CONTAINER_NAME = discord-gmusic-bot
DOCKER_OPTS = -v /app/data:$(shell pwd)/data

image:
	docker build . -t $(DOCKER_IMAGE_NAME)

run: image
	docker run $(DOCKER_OPTS) -it $(DOCKER_IMAGE_NAME)

stop:
	docker stop $(DOCKER_CONTAINER_NAME) || true
	docker rm $(DOCKER_CONTAINER_NAME) || true

daemon: stop image
	docker run $(DOCKER_OPTS) -d --name $(DOCKER_CONTAINER_NAME) $(DOCKER_IMAGE_NAME)
