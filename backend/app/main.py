import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import advisor, enrich, images, meta, profile


def _configure_advisor_logging() -> None:
    """Show Advisor diagnostics in the console and a local rotating log."""
    formatter = logging.Formatter(
        "%(asctime)s pid=%(process)d %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger_names = (
        "app.services.advisor_service",
        "app.services.gemini_title_service",
        "app.services.gemini_bundle_service",
        "app.services.psnprofiles_trophies_service",
    )
    service_loggers = [logging.getLogger(name) for name in logger_names]
    file_handler = next(
        (
            handler
            for service_logger in service_loggers
            for handler in service_logger.handlers
            if getattr(handler, "trophy_advisor_file", False)
        ),
        None,
    )
    if file_handler is None:
        log_dir = Path(__file__).resolve().parents[1] / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=2 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.trophy_advisor_file = True

    for service_logger in service_loggers:
        if not any(
            getattr(handler, "trophy_advisor_console", False)
            for handler in service_logger.handlers
        ):
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            handler.trophy_advisor_console = True
            service_logger.addHandler(handler)
        if file_handler not in service_logger.handlers:
            service_logger.addHandler(file_handler)
        service_logger.setLevel(logging.INFO)
        service_logger.propagate = False
    logging.getLogger("app.services.advisor_service").info(
        "Advisor rotating file log ready path=%s",
        getattr(file_handler, "baseFilename", "unknown"),
    )


def create_app() -> FastAPI:
    _configure_advisor_logging()
    app = FastAPI(title="Trophy Hunter API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(meta.router, prefix="/api")
    app.include_router(profile.router, prefix="/api")
    app.include_router(enrich.router, prefix="/api")
    app.include_router(advisor.router, prefix="/api")
    app.include_router(images.router, prefix="/api")
    return app


app = create_app()
