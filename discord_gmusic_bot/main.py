
import logging
import os
import sys
import toml

from .reloader import Reloader
from .gmusicbot import GMusicBot
from . import models


def main():
  logging.basicConfig(level=logging.INFO, format='[%(asctime)s - %(levelname)s]: %(message)s')

  # Load the configuration file.
  with open(os.path.normpath(__file__ + '/../../config.toml')) as fp:
    config = toml.load(fp)

  # Create a reloader and check if we're in the reloader's parent process.
  reloader_enabled = config['general'].get('use_reloader', config['general'].get('debug'))
  if reloader_enabled:
    reloader = Reloader()
    if not reloader.is_inner():
      argv = [sys.executable] + getattr(sys, '__argv__', sys.argv)
      reloader.run_forever(argv)
      return
  else:
    reloader = None

  # Connect to the database.
  if 'filename' in config['database']:
    config['database']['filename'] = os.path.abspath(config['database']['filename'])
  models.db.bind(**config['database'])
  models.migrate()
  models.db.generate_mapping(create_tables=True)

  # Run the bot.
  bot = GMusicBot(config, reloader)
  bot.run()
