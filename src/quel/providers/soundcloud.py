
from . import Provider, ProviderInstance, Song
from quel.core.utils import run_in_executor

import soundcloud


class SoundCloudProvider(Provider):

  id = 'soundcloud'
  name = 'SoundCloud'

  def get_option_names(self):
    return ['client_id']

  def instantiate(self, options):
    return SoundCloudInstance(self, options.get('client_id', None))


class SoundCloudInstance(ProviderInstance):

  def __init__(self, provider, client_id):
    super().__init__(provider)
    if not client_id:
      self.error = 'Missing client ID.'
      self.client = None
    else:
      self._client = soundcloud.Client(client_id=client_id)

  async def _get(self, *args, **kwargs):
    return await run_in_executor(None, lambda: self._client.get(*args, **kwargs))

  def _convert_resource(self, resource: soundcloud.resource.Resource) -> 'Song':
    """
    Helper function that converts a SoundCloud resource that represents a
    song to a #Song object. if the resource does not represent a song that
    is playable by this provider (eg. livestreams), a #ResolveError is
    raised.
    """

    if 'errors' in resource.fields():
      raise ResolveError(resource.errors[0]['error_message'])
    if resource.kind != 'track':
      raise ResolveError('Unable to play SoundCloud track {!r}'.format(resource.kind))
    #if not resource.streamable:
    #  raise ResolveError('Track is not streamable.')
    if 'finished' in resource.fields() and not resource.finished:
      raise ResolveError('Track is not finished.')

    return Song(
      url = resource.permalink_url,
      duration = resource.duration,
      title = resource.title,
      artist = resource.user['username'],
      genre = resource.genre,
      image_url = resource.artwork_url,
      stream_url = resource.stream_url,
      purchase_url = resource.purchase_url,
    )

  def supports_search(self):
    return True

  def match_url(self, url, urlinfo):
    # TODO: More sophisticated checking if the URL points to a song.
    return urlinfo.netloc == 'soundcloud.com', None

  async def search(self, term, max_results):
    songs_yielded = 0
    offset = 0
    while songs_yielded < max_results:
      for resource in await self._get('/tracks', q=term, limit=max_results, offset=offset):
        try:
          yield self._convert_resource(resource)
          songs_yielded += 1
        except ResolveError:
          pass
        if songs_yielded == max_results:
          break
      offset += max_results

  async def resolve_url(self, url, match_data):
    info = await self._get('/resolve', url=url)
    return self._convert_resource(info)

  async def get_stream_url(self, song):
    assert song.stream_url
    data = await self._get(song.stream_url, allow_redirects=False)
    return data.location
