# -*- coding: utf-8 -*-
"""Recommender module - backward compatibility re-export."""

from src.services.recommendation import (
    get_interest_recommendations,
    get_similar_recommendations,
    get_trending_recommendations,
)

__all__ = [
    "get_interest_recommendations",
    "get_similar_recommendations", 
    "get_trending_recommendations",
]
