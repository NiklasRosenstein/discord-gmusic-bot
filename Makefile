
image:
	docker build . -t discord-gmusic-bot

run: image
	docker run -it discord-gmusic-bot

deploy: image
	docker stop discord-gmusic-bot || true
	docker rm discord-gmusic-bot || true
	docker run -d --name discord-gmusic-bot discord-gmusic-bot
