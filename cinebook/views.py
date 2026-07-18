"""
CineBook — Global Error Views
==============================
Custom 404 and 500 handlers that never expose Django internals.
"""

import logging
from django.shortcuts import render

logger = logging.getLogger("cinebook.views")


def handler404(request, exception=None):
    """Return a custom 404 page — page not found."""
    return render(request, "errors/404.html", status=404)


def handler500(request):
    """Return a custom 500 page — never expose stack trace to client."""
    logger.error("500 Internal Server Error for request: %s %s", request.method, request.path)
    return render(request, "errors/500.html", status=500)
