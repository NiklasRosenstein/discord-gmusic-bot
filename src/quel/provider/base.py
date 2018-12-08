
import abc
import nr.types.named
import urllib.parse

from typing import *


class Song(nr.types.named.Named):
  url: str
  stream_url: Optional[str] = ''
  title: str
  artist: Optional[str] = ''
  genre: Optional[str] = ''
  album: Optional[str] = ''
  image_url: Optional[str] = ''
  duration: Optional[int] = ''
  purchase_url: Optional[str] = ''


class ResolveError(Exception):
  pass


class Provider(metaclass=abc.ABCMeta):

  def __init__(self):
    pass

  @classmethod
  def get_options(cls) -> List[str]:
    code = cls.__init__.__code__
    return code.co_varnames[1:code.co_argcount]

  @classmethod
  @abc.abstractmethod
  def get_provider_name(self) -> str:
    pass

  @abc.abstractmethod
  def does_support_search(self) -> bool:
    pass

  async def search(self, term: str, max_results: int) -> AsyncIterable[Song]:
    raise NotImplementedError

  @classmethod
  @abc.abstractmethod
  async def matches_url(self, url: str, urlinfo: urllib.parse.ParseResult) -> bool:
    pass

  @abc.abstractmethod
  async def resolve(self, url) -> Song:
    pass

  @abc.abstractmethod
  async def get_stream_url(self, song: Song) -> str:
    pass
