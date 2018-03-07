
from pony.orm import *
import gmusicapi
from .drivers import soundcloud

db = Database()
session = db_session


class Server(db.Entity):

  id = PrimaryKey(str)
  volume = Required(int, default=50)

  # Reverse members
  gmusic_credentials = Optional('GMusicCredentials')
  soundcloud_id = Optional('SoundcloudID')

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


class SoundcloudID(db.Entity):

  server = PrimaryKey(Server)
  client_id = Required(str)

  def get_soundcloud_client(self):
    return soundcloud.Client(self.client_id)


class MigrationIndex(db.Entity):

  id = PrimaryKey(int)  # Always 1
  index = Required(int)


@session
def migrate(dry=False):
  migrations = [v for k, v in globals().items() if k.startswith('migration_')]
  migrations.sort(key=lambda x: x.__name__)
  max_index = len(migrations) - 1

  # TODO: This probably only works with SQLite as the backend.
  query = "COUNT(*) FROM sqlite_master WHERE type='table' AND name='MigrationIndex'"
  if db.select(query)[0]:
    have_index = next(iter(db.select("[index] FROM MigrationIndex WHERE id=1")), None)
  else:
    have_index = None

  def update_migration_index():
    nonlocal max_index
    print('Updating MigrationIndex to {}'.format(max_index))
    db.execute('INSERT OR IGNORE INTO MigrationIndex VALUES (1, $max_index)')
    db.execute('UPDATE MigrationIndex SET [index]=$max_index WHERE id=1')

  if have_index is None:
    print('note: no MigrationIndex found, assuming latest revision')
    db.execute('''CREATE TABLE IF NOT EXISTS MigrationIndex (
                  id PRIMARY KEY INTEGER, index INTEGER)''')
    update_migration_index()
  else:
    if have_index > max_index:
      print('warning: have migration index {} where the maximum is {}'
          .format(have_index, max_index))
    if have_index >= max_index:
      return
    print('Migrating database from {} to {} ...'.format(have_index, len(migrations)-1))
    for index in range(have_index + 1, len(migrations)):
      print('  migration {}'.format(index))
      migrations[index]()
    update_migration_index()

  if dry:
    print('Dry migration requested, rolling back ...')
    rollback()
  else:
    print('Commiting migration sequence ...')
    commit()


def migration_000():
  pass


def migration_001():
  """
  Adds #Server.volume.
  """

  db.execute('''
    ALTER TABLE Server ADD COLUMN volume INTEGER NOT NULL DEFAULT 50
  ''')
