
import json
import requests
import urllib.parse


class Client:
  """
  A simple unofficial SoundCloud client. Requires a client ID. You can
  retrieve this client ID by checking your browser's developer console
  on the SoundCloud page after logging in.
  """

  class Error(Exception):
    pass

  def __init__(self, client_id):
    self.client_id = client_id

  def annotate(self, url, params=None):
    """
    Annotates the specified *url* with the URL parameters *params* plus
    the SoundCloud client ID.
    """

    if not params:
      params = {}
    else:
      params = params.copy()

    params['client_id'] = self.client_id
    return url + '?' + urllib.parse.urlencode(params)

  def request(self, url, params=None, check=True, **kwargs):
    """
    Performs a request, adding the SoundCloud client ID to the URL parameters
    specified with *params*. If *check* is True (default), a non-200 response
    will raise an #Error.
    """

    if params is None:
      params = {}
    else:
      params = params.copy()

    params['client_id'] = self.client_id
    response = requests.get(url, params=params, **kwargs)

    if check:
      try:
        response.raise_for_status()
      except requests.RequestException as e:
        raise self.Error() from e

    return response

  def resolve(self, url):
    """
    Returns the track information for a SoundCloud URL.
    """

    endpoint = 'http://api.soundcloud.com/resolve.json'
    return self.request(endpoint, {'url': url}).json()
