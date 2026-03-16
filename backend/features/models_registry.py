"""Import SQLAlchemy model modules so Alembic autogenerate can discover them."""

from features.auth import models as auth_models  # noqa: F401

# Add future feature model imports here, for example:
# from features.products import models as products_models  # noqa: F401
