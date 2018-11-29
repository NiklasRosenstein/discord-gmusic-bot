

def create_or_update(_entity, _key, **update):
  obj = get_or_create(_entity, _key, **update)
  if obj:
    for key, value in update.items():
      setattr(obj, key, value)
  return obj


def get_or_create(_entity, _key, **update):
  obj = _entity.get(**_key)
  if not obj:
    obj = _entity(**_key, **update)
  return obj
