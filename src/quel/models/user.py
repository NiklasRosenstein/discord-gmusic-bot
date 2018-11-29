
from . import db
from .utils import create_or_update, get_or_create
from pony import orm


class User(db.Entity):
  id = orm.PrimaryKey(str)
  name = orm.Required(str)
  avatar_url = orm.Optional(str)

  @classmethod
  def for_discord_user(cls, user, update=True):
    method = create_or_update if update else get_or_create
    return method(cls, {'id': user.id}, name=user.name,
      avatar_url=user.avatar_url)
