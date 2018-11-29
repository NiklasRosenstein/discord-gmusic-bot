
import argparse
import urllib.parse

from . import providers


async def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('arg')
  parser.add_argument('-q', '--search')
  parser.add_argument('-d', '--download-url', action='store_true')
  args, argv = parser.parse_known_args()

  # Parse additional options.
  options = {}
  it = iter(argv)
  while True:
    try: value = next(it)
    except StopIteration: break
    if not value.startswith('--') or len(value) == 2:
      parser.error('unknown argument {!r}'.format(value))
    if '=' in value:
      name, value = value[2:].partition('=')[::2]
    else:
      name = value[2:]
      try: value = next(it)
      except StopIteration:
        parser.error('missing option value for --{}'.format(name))
    options[name] = value

  def create_provider(provider_cls):
    kwargs = {}
    for option in provider_cls.get_options():
      if option not in options:
        parser.error('missing option {!r}'.format(option))
      kwargs[option] = options[option]
    return provider_cls(**kwargs)

  if args.search:
    provider_cls = providers[args.search]
    provider = create_provider(provider_cls)
    async for song in provider.search(args.arg, 10):
      print(song.title)
  else:
    urlinfo = urllib.parse.urlparse(args.arg)
    for provider_cls in providers.values():
      if provider_cls.matches_url(args.arg, urlinfo):
        break
    else:
      parser.error('unable to match {!r}'.format(args.arg))
    provider = create_provider(provider_cls)
    song = await provider.resolve(args.arg)
    if args.download_url:
      print(await provider.get_stream_url(song))
    else:
      print(song.title)


if __name__ == '__main__':
  import asyncio, sys
  sys.exit(asyncio.get_event_loop().run_until_complete(main()))
