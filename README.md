## discord-gmusic-bot (WIP)

A Discord bot that plays music via Google Play Music or from Youtube.

__To do__

* Implement playlist/queue, searching for a title, etc.
* Ability to configure a special channel, where you don't need to address the
  bot specifically with a prefix
* Stream audio from GMusic instead of caching files into the `song_cache/` directory?
  Streaming the HTTPResponse into `create_ffmpeg_player()` (using a `os.pipe()`)
  gives an ffmpeg warning `[mp3 @ 0000000000d62340] invalid concatenated file detected - using bitrate for duration`,
  probably because the file size can not be determined.

### Usage

If you have a text-channel where the topic contains the string
`discord-gmusic-bot`, any message is considered a command for the bot. In any
other channel, you will need to mention the bot first.

Send `help` to get a list of available commands.

### Installation & Deployment

__1. Discord Permissions__ (`3148800`)

* Text : Read Messages
* Text : Send Messages
* Voice : View Channel
* Voice : Connect
* Voice : Speak

__2. Installing the Opus Codec__

Follow the [Installing libopus] instructions. On Windows, Discord.py comes
with a version of `libopus-0.x86.dll` and `libopus-0.x64.dll`, so you only
need to use the right name depending on your Python version in `config.py`.

Alternatively, you can download a Windows opus build from the [Opus download]
page for Windows x86 or from the [craftr-libopus] repository for Windows x64.

  [craftr-libopus]: https://github.com/NiklasRosenstein/craftr-libopus/releases
  [Installing libopus]: https://github.com/meew0/discordrb/wiki/Installing-libopus
  [Opus download]: http://opus-codec.org/downloads/

__3. Create an App-specific password for your Google Account__

This can be done under https://myaccount.google.com/apppasswords and is
necessary for accounts secured by two-factor authentication, yet still
recommended in general.

__4. Getting up and running__

    $ pip3 install nodepy-runtime
    $ nodepy https://nodepy.org/install-pm.py
    $ git clone https://github.com/NiklasRosenstein/discord-music-bot.git
    $ cd discord-music-bot
    $ cp config.example.py config.py
    $ $(EDITOR) config.py
    $ nodepy-pm install
    $ nodepy .

You should see a URL that allows you to add the bot to your server printed
in the console. Press CTRL+C to stop the bot. *Note: The discord API or the
asyncio module in Python seem to have a long delay from you pressing CTRL+C
and raising a KeyboardInterrupt exception.*

### Useful Tools

* https://discordapi.com/permissions.html
* https://leovoel.github.io/embed-visualizer/
