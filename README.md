## discord-gmusic-bot (WIP)

A Discord bot that plays music via Google Play Music or Youtube.

__To do__

* Stream audio from GMusic instead of caching files into the `song_cache/` directory?

    > Streaming the HTTPResponse into `create_ffmpeg_player()` (using a `os.pipe()`)
    > gives an ffmpeg warning, probably because the file size can not be determined.
    > It seems that the file size can not be properly determined, isn't played
    > for it's whole duration.
    >
    >     [mp3 @ 0000000000d62340] invalid concatenated file detected - using bitrate for duration

* Read out YouTube Video Title
* Support YouTube and Google Music Playlists
* Understand exclamation mark in `play <query>!` to immediately play the song
* Add commands to remove/reorder items in the queue

### Usage

If you have a text-channel where the topic contains the string
`discord-gmusic-bot`, any message is considered a command for the bot. In any
other channel, you will need to mention the bot first.

Send `help` to get a list of available commands.

![](https://i.imgur.com/1HFDCmY.png)

### Requirements

__Discord Permissions__ (`3148800`)

* Text : Read Messages
* Text : Send Messages
* Voice : View Channel
* Voice : Connect
* Voice : Speak

__Software/Libraries__

* CPython 3
* ffmpeg
* libopus

__Google Music Account + App-specific password__

This can be done under https://myaccount.google.com/apppasswords and is
necessary for accounts secured by two-factor authentication, yet still
recommended in general.


### Installation

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


### Installation (Windows Appendix)

__libopus__

On Windows, Discord.py comes with a version of `libopus-0.x86.dll` and
`libopus-0.x64.dll`, so you only need to use the right name depending on your
Python version in `config.py`.

Alternatively, you can download a Windows opus build from the [Opus download]
page for Windows x86 or from the [craftr-libopus] repository for Windows x64.

  [craftr-libopus]: https://github.com/NiklasRosenstein/craftr-libopus/releases
  [Installing libopus]: https://github.com/meew0/discordrb/wiki/Installing-libopus
  [Opus download]: http://opus-codec.org/downloads/

__ffmpeg__

FFmpeg must be in your `PATH` in order to stream music to the Discord bot.
Windows builds can be found [here](https://www.ffmpeg.org/download.html).


### Useful Tools

* https://discordapi.com/permissions.html
* https://leovoel.github.io/embed-visualizer/
