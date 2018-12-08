
from . import Quel, models

import argparse
import json
import logging
import os


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('-c', '--config', default='config.json')
  parser.add_argument('-v', '--verbose', action='store_true')
  args = parser.parse_args()

  with open(args.config) as fp:
    config = json.load(fp)

  loglevel = logging.INFO if args.verbose else logging.WARNING
  logformat = config.get('logging', {}).get('format')
  if not logformat:
    logformat = '[%(levelname)s %(name)s %(asctime)s]: %(message)s'
  logging.basicConfig(format=logformat, level=loglevel)

  #if not reloader.is_inner():
  #  return reloader.run_forever()

  bot = Quel(config)
  bot.run(config['botConfig']['token'])
  bot.logger.info('Bye bye.')


if __name__ == '__main__':
  main()
