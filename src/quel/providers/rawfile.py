
from . import Provider, ProviderInstance, Song
from urllib.parse import urlparse

import posixpath


class RawFileProvider(Provider, ProviderInstance):

  id = 'rawfile'
  name = 'File/URL'
  error = None

  def __init__(self):
    pass

  @property
  def provider(self):
    return self

  def instantiate(self, options):
    return self

  def match_url(self, url, urlinfo):
    ext = urlinfo.path.rpartition('.')[-1]
    return ext in ('mp3', 'wav')

  async def resolve_url(self, url):
    title = posixpath.basename(urlparse(url).path)
    return Song(url, title=title, artist='Unknown')

  async def get_stream_url(self, song):
    return song.url
