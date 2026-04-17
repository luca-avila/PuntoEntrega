"""Import SQLAlchemy model modules so Alembic autogenerate can discover them."""

from features.auth import models as auth_models  # noqa: F401
from features.deliveries import models as deliveries_models  # noqa: F401
from features.invitations import models as invitations_models  # noqa: F401
from features.locations import models as locations_models  # noqa: F401
from features.notifications import models as notifications_models  # noqa: F401
from features.organizations import models as organizations_models  # noqa: F401
from features.product_requests import models as product_requests_models  # noqa: F401
from features.products import models as products_models  # noqa: F401

# Add future feature model imports here.
