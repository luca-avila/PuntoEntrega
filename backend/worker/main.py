import asyncio

from core.logging import configure_logging
import features.models_registry  # noqa: F401
from features.notifications.worker import run_worker_forever


def main() -> None:
    configure_logging()
    asyncio.run(run_worker_forever())


if __name__ == "__main__":
    main()
