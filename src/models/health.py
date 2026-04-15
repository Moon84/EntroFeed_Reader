# -*- coding: utf-8 -*-
"""Health check model for EntroFeed."""

from pydantic import BaseModel


class HealthCheck(BaseModel):
    """Health check response model."""

    status: str = "OK"
