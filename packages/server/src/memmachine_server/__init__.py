"""Public package exports and utilities for MemMachine server."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from memmachine_server.main.memmachine import MemMachine as MemMachine


def __getattr__(name: str) -> Any:
    if name == "MemMachine":
        from memmachine_server.main.memmachine import MemMachine as _MemMachine

        return _MemMachine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def setup_nltk() -> None:
    """Check for and download required NLTK data packages."""
    import logging

    import nltk

    logger = logging.getLogger(__name__)

    logger.info("Checking for required NLTK data...")
    packages = [
        ("tokenizers/punkt", "punkt"),
        ("tokenizers/punkt_tab", "punkt_tab"),
        ("corpora/stopwords", "stopwords"),
    ]
    for path, pkg_id in packages:
        try:
            nltk.data.find(path)
            logger.info("NLTK package '%s' is already installed.", pkg_id)
        except LookupError:
            logger.warning("NLTK package '%s' not found. Downloading...", pkg_id)
            nltk.download(pkg_id)
    logger.info("NLTK data setup is complete.")


__all__ = ["MemMachine", "setup_nltk"]
