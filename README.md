# Quel

Quel is a simple music bot for Discord and is the successor of *discord-gmusic-bot*.

## Features

* Plays from MP3/WAV attachments and URLs
* Supports searching and playing from SoundCloud (YouTube and GoogleMusic are planned)

## Installation

You need to register a Discord bot and turn it into a "bot user". The bot
requires the following permissions: https://discordapi.com/permissions.html#70274048

1. Clone this repository
2. Copy the `config.json.template` to a file named `config.json` and fill in the Discord token
3. Run `docker-compose up -d`

If you disable "Embed Links" on the bot's main channel (so that Discord does
not automatically generate embeds for pasted links), you need to give it a
role that grants these embed permissions specifically to the bot.

## Usage

The bot currently reacts on messages when it was mentioned at the beginning of the message, or
messages sent to a channel that contains the string "Quel".

### Setting up the SoundCloud Client ID

Go to https://soundcloud.com, open your browser's network tab and copy the `client_id` that is
sent by SoundCloud in most requests. Paste this ID below when sending the bot the following command:

    config set soundcloud.client_id <client_id>

You can check for the status of all available providers using the `provider status` command.

### Playing/queueing/searching

The `play <urls>` and `queue [<urls>]` commands accept one or more URLs (separated by semicolons `;`). Basic
controls are available with the `resume`, `pause`, `stop`, `volume [<vol>]` and `clear queue` commands.

The `search <term>` command can be used to search all available providers using a search term. You
can search only a specific provider using the syntax `search <provider>: <term>`.

## Useful Development Links

* https://discordapi.com/permissions.html
* https://leovoel.github.io/embed-visualizer/
