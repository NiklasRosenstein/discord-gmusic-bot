
import logging
import toml
import nodepy.runtime
import sys

import Reloader from './reloader'
import GMusicBot from './gmusicbot'


def main():
  logging.basicConfig(level=logging.INFO)

  # Load the configuration file.
  with module.package.directory.joinpath('config.toml').open() as fp:
    config = toml.load(fp)

  # Create a reloader and check if we're in the reloader's parent process.
  reloader = Reloader()
  if config['debug']['use_reloader'] and not reloader.is_inner():
    argv = nodepy.runtime.exec_args + [str(module.filename)]
    reloader.run_forever(argv)
    return

  # Run the bot.
  bot = GMusicBot(config, reloader)
  bot.run()


if require.main == module:
  sys.exit(main())
