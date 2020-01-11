def has_attributes(obj: object, name: str) -> bool:
    attr = getattr(obj, name, None)
    if attr is None:
        return False
    return True
