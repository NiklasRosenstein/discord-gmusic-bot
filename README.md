## discord-gmusic-bot (WIP)

A Discord bot that plays music via Google Play Music or Youtube.

### Usage

Either mention `@discord-gmusic-bot` or create a separate channel that
contains the string `discord-gmusic-bot` in its title to talk to the bot.
Send `help` to get a list of available commands.

<p align="center">
  <img src="https://i.imgur.com/1HFDCmY.png"/>
<p>

### Get Started

    $ cp config.example.toml config.toml && $(EDITOR) config.toml
    $ docker build . -t discord-gmusic-bot
    $ docker run discord-gmusic-bot
    [...]
    INFO:discord-gmusic-bot:        https://discordapp.com/oauth2/authorize?client_id=282709421955576523&scope=bot&permissions=3148800

### Requirements

1. Your [own Discord bot](https://discordapp.com/developers/applications/me/create)
2. Make sure to promote the Bot to a "Bot User"
3. A Google Music Account plus an [app specific password](https://myaccount.google.com/apppasswords)

### To do

* Ability to bulk-queue songs (eg. from a YouTube playlist or multiple links)
* Support YouTube and Google Music Playlists
* Understand exclamation mark in `play <query>!` to immediately play the song
* Add commands to remove/reorder items in the queue
* Maybe use [tizonia](https://github.com/tizonia/tizonia-openmax-il) as the
  music streaming backend

### Useful Tools

* https://discordapi.com/permissions.html
* https://leovoel.github.io/embed-visualizer/
