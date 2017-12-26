
image:
	docker build . -t discord-gmusic-bot

run: image
	docker run -it discord-gmusic-bot
