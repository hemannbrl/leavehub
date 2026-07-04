def role(user):
    return getattr(getattr(user, "profile", None), "role", None)
