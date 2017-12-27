
from pony.orm import *
import gmusicapi

db = Database()
session = db_session


class Server(db.Entity):

  id = PrimaryKey(str)
  gmusic_credentials = Optional('GMusicCredentials')

  @classmethod
  def get_or_create(cls, *, id):
    server = cls.get(id=id)
    if not server:
      server = Server(id=id)
    return server


class GMusicCredentials(db.Entity):

  # Keeps track of gmusicapi.Mobileclient instances created during the
  # runtime of the bot.
  GMUSIC_INSTANCES = {}

  server = PrimaryKey(Server)
  username = Required(str)
  password = Required(str)

  def get_gmusic_client(self):
    try:
      return self.GMUSIC_INSTANCES[self.server.id]
    except KeyError:
      pass
    instance = gmusicapi.Mobileclient(debug_logging=False)
    if not instance.login(self.username, self.password, gmusicapi.Mobileclient.FROM_MAC_ADDRESS):
      instance = None
    self.GMUSIC_INSTANCES[self.server.id] = instance
    return instance

  def before_delete(self):
    self.GMUSIC_INSTANCES.pop(self.server.id, None)

  def before_update(self):
    self.GMUSIC_INSTANCES.pop(self.server.id, None)
