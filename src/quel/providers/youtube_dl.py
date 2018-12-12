
from . import Provider, ProviderInstance, ResolveError, Song
from quel.core.utils import run_in_executor
from youtube_dl import DownloadError, YoutubeDL
from youtube_dl.extractor import list_extractors
from youtube_dl.extractor.generic import GenericIE

import logging
logger = logging.getLogger(__name__)


class YoutubeDlProvider(Provider):

  id = 'youtube_dl'
  name = 'YouTubeDL'
  default_search_whitelist = ['ytsearch']

  def __init__(self, allow_video_stream=False, search_whitelist=None):
    if search_whitelist is None:
      search_whitelist = list(self.default_search_whitelist)
    self.allow_video_stream = allow_video_stream
    self.search_whitelist = search_whitelist

  def instantiate(self, options):
    return YoutubeDlProviderInstance(self)


class YoutubeDlProviderInstance(ProviderInstance):

  search_keys = {
    getattr(ie, 'SEARCH_KEY', None): ie.ie_key()
    for ie in list_extractors(18)
  }
  search_keys.pop(None, None)

  def __init__(self, provider):
    super().__init__(provider)
    self.yt = YoutubeDL()

  def _convert_response(self, data) -> Song:
    tracks = data['formats']
    if not self.provider.allow_video_stream:
      tracks = [x for x in tracks if 'width' not in x]
    if not tracks:
      raise ResolveError('No suitable tracks found')

    # TODO @NiklasRosenstein replace this poor mans method of finding the best quality format
    track = max(tracks, key=lambda x: x['filesize'])
    thumbnail = next((x['url'] for x in data['thumbnails']), None)

    return Song(
      data['webpage_url'],
      stream_url = track['url'],
      title = data['title'],
      artist = data['uploader'],
      image_url = thumbnail,
      duration = data['duration']
    )

  def supports_search(self):
    return True

  async def search(self, term, max_results):
    for search_key in self.provider.search_whitelist:
      if search_key in self.search_keys:
        ie_key = self.search_keys[search_key]
        query = '{}{}:{}'.format(search_key, int(max_results), term)
        try:
          data = await run_in_executor(None,
            lambda: self.yt.extract_info(query, download=False, ie_key=ie_key))
        except DownloadError as exc:
          return; yield
        for entry in data['entries']:
          try:
            yield self._convert_response(entry)
          except ResolveError as exc:
            logger.warning('ResolveError when converting response from "{}": {}'.format(search_key, exc))

  def match_url(self, url, urlinfo):
    for ie in list_extractors(18):
      if not isinstance(ie, GenericIE) and ie.suitable(url):
        return True, ie
    return False, None

  async def resolve_url(self, url, ie):
    try:
      data = await run_in_executor(None,
        lambda: self.yt.extract_info(url, download=False, ie_key=ie.ie_key()))
    except DownloadError:
      raise ResolveError('Unable to extract information from URL')
    return self._convert_response(data)

  async def get_stream_url(self, song):
    return song.stream_url
