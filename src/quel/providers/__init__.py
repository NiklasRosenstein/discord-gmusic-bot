
from nr.types.named import Named
from typing import *


class Provider:

  id = None
  name = None

  def get_option_names(self):
    return []

  def instantiate(self, options):
    raise NotImplementedError


class ProviderInstance:

  error = None

  def __init__(self, provider):
    self.provider = provider

  @property
  def id(self):
    return self.provider.id

  @property
  def name(self):
    return self.provider.name


class ErrorProviderInstance(ProviderInstance):

  def __init__(self, provider, error):
    super().__init__(provider)
    self.error = error

  def supports_searching(self):
    return False

  async def search(self, term, max_results):
    return []

  def match_url(self, url, urlinfo):
    raise NotImplementedError

  async def resolve_url(self, url):
    raise NotImplementedError

  async def get_stream_url(self, song):
    raise NotImplementedError


class Song(Named):
  url: str
  stream_url: Optional[str] = ''
  title: str
  artist: Optional[str] = ''
  genre: Optional[str] = ''
  album: Optional[str] = ''
  image_url: Optional[str] = ''
  duration: Optional[int] = ''
  purchase_url: Optional[str] = ''
