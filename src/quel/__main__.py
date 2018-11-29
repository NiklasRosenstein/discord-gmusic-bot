
from quel import models
from quel.bot import bot, reloader, logger

import json
import logging
import os
import quel


def main():
  logging.basicConfig(format='[%(levelname)s %(name)s %(asctime)s]: %(message)s', level=logging.INFO)

  #if not reloader.is_inner():
  #  return reloader.run_forever()

  with open('config.json') as fp:
    config = json.load(fp)
  quel.bot.config = config

  if 'filename' in config['dbConfig']:
    config['dbConfig']['filename'] = os.path.abspath(config['dbConfig']['filename'])

  models.db.bind(**config['dbConfig'])
  models.db.generate_mapping(create_tables=True)
  bot.run(config['botConfig']['token'])
  logger.info('Bye bye.')


if __name__ == '__main__':
  main()
