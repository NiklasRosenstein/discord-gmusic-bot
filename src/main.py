
import logging
import nodepy.runtime
import os
import sys
import toml

import Reloader from './reloader'
import GMusicBot from './gmusicbot'
import models from './models'


def main():
  logging.basicConfig(level=logging.INFO, format='[%(asctime)s - %(levelname)s]: %(message)s')

  # Load the configuration file.
  with module.package.directory.joinpath('config.toml').open() as fp:
    config = toml.load(fp)

  # Create a reloader and check if we're in the reloader's parent process.
  reloader_enabled = config['general'].get('use_reloader', config['general'].get('debug'))
  if reloader_enabled:
    reloader = Reloader()
    if not reloader.is_inner():
      argv = nodepy.runtime.exec_args + [str(module.filename)]
      reloader.run_forever(argv)
      return
  else:
    reloader = None

  # Connect to the database.
  if 'filename' in config['database']:
    config['database']['filename'] = os.path.abspath(config['database']['filename'])
  models.db.bind(**config['database'])
  models.db.generate_mapping(create_tables=True)

  # Run the bot.
  bot = GMusicBot(config, reloader)
  bot.run()


if require.main == module:
  sys.exit(main())
