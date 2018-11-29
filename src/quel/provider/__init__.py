
from .base import Provider, Song, ResolveError
from .soundcloud import SoundCloudProvider

available_providers = {
  'soundcloud': SoundCloudProvider
}
