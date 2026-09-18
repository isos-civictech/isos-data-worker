"""Container entry point: `python -m src.main`."""
import uvicorn

from src.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "src.interfaces.api.app:create_app",
        factory=True,
        host=settings.api_host,
        port=settings.api_port,
        log_config=None,  # loguru already writes to stdout; two configs means double lines
    )


if __name__ == "__main__":
    main()
