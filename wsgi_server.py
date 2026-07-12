"""Production-grade WSGI serving helper for BigCoin full nodes.

Flask's built-in development server saturates under high concurrent request
load (e.g. many peers polling /api/blockchain/info). This module provides a
single `serve()` helper that prefers the `waitress` production WSGI server
when it is installed, falling back gracefully to Flask's dev server otherwise.
"""

import logging

logger = logging.getLogger(__name__)


def serve(app, host: str, port: int, threads: int = 16) -> None:
    """Serve a Flask/WSGI `app` using waitress if available, else fall back
    to Flask's built-in server. waitress is a production WSGI server that
    handles high concurrent connections far better than Flask's dev server."""
    try:
        from waitress import serve as _waitress_serve
    except ImportError:
        print(
            f"[wsgi_server] WARNING: 'waitress' is not installed; falling back "
            f"to the Flask development server on {host}:{port}. "
            f"For production/high-concurrency use, install it with: "
            f"pip install waitress"
        )
        logger.warning(
            "waitress not available; using Flask dev server on %s:%s "
            "(install waitress for production use)",
            host,
            port,
        )
        app.run(host=host, port=port, threaded=True, use_reloader=False)
        return

    print(
        f"[wsgi_server] Serving with waitress (production WSGI) on "
        f"{host}:{port} using {threads} threads"
    )
    logger.info(
        "Serving with waitress on %s:%s (threads=%d)", host, port, threads
    )
    _waitress_serve(app, host=host, port=port, threads=threads)


def _waitress_available() -> bool:
    """Return True if the waitress package can be imported."""
    try:
        import waitress  # noqa: F401
    except ImportError:
        return False
    return True


if __name__ == "__main__":
    # Report availability without starting a blocking server.
    if _waitress_available():
        print("waitress is available: serve() will use the production WSGI server.")
    else:
        print(
            "waitress is NOT available: serve() will fall back to the Flask "
            "dev server. Install it with: pip install waitress"
        )
