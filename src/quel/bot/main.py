
from . import Quel
from quel import models

import argparse
import json
import logging
import os
import sys

logger = logging.getLogger('quel.bot.main')


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('-c', '--config', default='config.json')
  parser.add_argument('-v', '--verbose', action='store_true')
  parser.add_argument('-r', '--reload', action='store_true')
  args = parser.parse_args()

  with open(args.config) as fp:
    config = json.load(fp)

  loglevel = logging.INFO if args.verbose else logging.WARNING
  logformat = config.get('logging', {}).get('format')
  if not logformat:
    logformat = '[%(levelname)s %(name)s %(asctime)s]: %(message)s'
  logging.basicConfig(format=logformat, level=loglevel)

  bot = Quel(config)

  if args.reload and not bot.reloader.is_inner():
    logger.info('Starting reloader ...')
    return bot.reloader.run_forever([sys.executable, '-m', 'quel.bot.main'] + sys.argv[1:])

  logger.info('Binding database ...')
  if 'filename' in config['dbConfig']:
    config['dbConfig']['filename'] = os.path.abspath(config['dbConfig']['filename'])
  models.db.bind(**config['dbConfig'])
  models.db.generate_mapping(create_tables=True)

  logger.info('Starting ...')
  bot.run(config['botConfig']['token'])
  logger.info('Bye bye.')


if __name__ == '__main__':
  main()
