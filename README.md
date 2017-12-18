## discord-gmusic-bot (WIP)

A Discord bot that plays music via Google Play Music.

### Installation & Deployment

__Discord Permissions__

* Text : Read Messages
* Text : Send Messages
* Text : Add Reactions
* Voice : View Channel
* Voice : Connect
* Voice : Speak

__Installing the Opus Codec__

Follow the [Installing libopus] instructions.

__Installing the Opus Codec (Windows)__

If you're using a 32-bit Python version, again follow the [Installing libopus]
instructions. The binaries provided on the Opus website are no 64-bit versions,
so if you're using a 64-bit Python version, grab a pre-compiled version of Opus
from the [craftr-libopus] repository.

Place the pre-compiled `opus.dll` in the `discord-gmusic-bot` directory.

  [craftr-libopus]: https://github.com/NiklasRosenstein/craftr-libopus/releases
  [Installing libopus]: https://github.com/meew0/discordrb/wiki/Installing-libopus

__Create an App-specific password for your Google Account__

This can be done under https://myaccount.google.com/apppasswords and is
necessary for accounts secured by two-factor authentication, yet still
recommended in general.

__Getting up and running__

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
