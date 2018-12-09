
from . import Provider, ProviderInstance, ResolveError, Song
from quel.core.utils import run_in_executor
from youtube_dl import YoutubeDL
from youtube_dl.extractor import list_extractors
from youtube_dl.extractor.generic import GenericIE


class YoutubeDlProvider(Provider):

  id = 'youtube_dl'
  name = 'YouTubeDL'

  def __init__(self, allow_video_stream=False):
    self.allow_video_stream = allow_video_stream

  def instantiate(self, options):
    return YoutubeDlProviderInstance(self)


class YoutubeDlProviderInstance(ProviderInstance):

  def __init__(self, provider):
    super().__init__(provider)
    self.yt = YoutubeDL()

  def supports_searching(self):
    return False

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
      return ResolveError('Unable to extract information from URL')

    tracks = data['formats']
    if not self.provider.allow_video_stream:
      tracks = [x for x in tracks if 'width' not in x]
    if not tracks:
      raise ResolveError('No suitable tracks found')

    # TODO @NiklasRosenstein replace this poor mans method of finding the best quality format
    track = max(audio_tracks, key=lambda x: x['filesize'])
    thumbnail = next((x['url'] for x in data['thumbnails']), None)

    return Song(
      url,
      stream_url = track['url'],
      title = data['title'],
      artist = data['uploader'],
      image_url = thumbnail,
      duration = data['duration']
    )

  async def get_stream_url(self, song):
    return song.stream_url
