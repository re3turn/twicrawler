def has_attributes(obj: object, name: str) -> bool:
    attr = getattr(obj, name, None)
    if not attr:
        return False
    return True
