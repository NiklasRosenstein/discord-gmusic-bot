
def get_or_create(_entity, _key, **update):
  obj = _entity.get(**_key)
  if not obj:
    obj = _entity(**_key, **update)
  return obj


def create_or_update(_entity, _key, **update):
  obj = get_or_create(_entity, _key, **update)
  if obj:
    for key, value in update.items():
      setattr(obj, key, value)
  return obj


class durable_member:

  data = {}

  def __init__(self, default_factory):
    self.default_factory = default_factory

  def _get_key(self, obj):
    pk = tuple(getattr(obj, a.name) for a in obj._pk_attrs_)
    return (type(obj), pk, self)

  def __get__(self, obj, _=None):
    key = self._get_key(obj)
    try:
      return self.data[key]
    except KeyError:
      value = self.default_factory()
      self.data[key] = value
      return value

  def __set__(self, obj, value):
    key = self._get_key(obj)
    self.data[key] = value
