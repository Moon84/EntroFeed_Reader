# -*- coding: utf-8 -*-
"""
EntroFeed Recommender - Content recommendation system.

Provides:
- Similar content recommendation using vector search
- Interest-based recommendation
- Trending content recommendation
"""
from src.services.recommendation.similar import SimilarRecommender, get_similar_recommendations
from src.services.recommendation.interest_based import InterestBasedRecommender, get_interest_recommendations
from src.services.recommendation.trending import TrendingRecommender, get_trending_recommendations

__all__ = [
    "SimilarRecommender",
    "InterestBasedRecommender",
    "TrendingRecommender",
    "get_similar_recommendations",
    "get_interest_recommendations",
    "get_trending_recommendations",
]
