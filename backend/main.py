import uvicorn

from backend.app.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "backend.app.server:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()

