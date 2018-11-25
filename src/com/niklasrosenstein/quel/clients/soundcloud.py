
"""
A very basic SoundCloud client.
"""

import asyncio
import json
import requests
import urllib.parse


class Error(Exception):
  pass


class SoundCloudClient:
  """
  :param client_id: You can retrieve this client ID by checking your browser's
    developer console on the SoundCloud page after logging in.
  """

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

  async def request(self, url, params=None, check=True, **kwargs):
    """
    Performs a request, adding the SoundCloud client ID to the URL parameters
    specified with *params*. If *check* is True (default), a non-200 response
    will raise an #Error.
    """

    loop = asyncio.get_running_loop()

    if params is None:
      params = {}
    else:
      params = params.copy()

    params['client_id'] = self.client_id
    response = await loop.run_in_executor(
      None, requests.get, url, params=params, **kwargs)

    if check:
      response.raise_for_status()

    return response

  async def resolve(self, url):
    """
    Returns the track information for a SoundCloud URL.

    The returned JSON payload contains the following keys amongst others:

    * kind (eg. track)
    * streamable
    * title
    * genre (optional?)
    * artwork_url (optional?)
    * stream_url
    """

    endpoint = 'http://api.soundcloud.com/resolve.json'
    return self.request(endpoint, {'url': url}).json()
