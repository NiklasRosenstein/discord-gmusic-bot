
from pony import orm
from . import db


class DiscordServer(db.Entity):
  id = orm.PrimaryKey(str)
  options = orm.Required(orm.Json)
