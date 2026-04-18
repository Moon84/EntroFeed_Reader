#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Evaluation Script - Analyze scoring system on real data.

This script:
1. Loads real entries from SQLite database
2. Loads user interests from ontology
3. Runs scoring pipeline on all entries
4. Outputs score distribution analysis and statistics
"""
import sys
import os
import sqlite3
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import only what we need for scoring
from src.services.ontology import get_ontology_registry


def load_entries_from_db(limit: int = 500) -> List[Dict[str, Any]]:
    """Load recent entries from database.

    Args:
        limit: Maximum number of entries to load

    Returns:
        List of entry dictionaries
    """
    # Direct SQLite access to avoid loading entire app
    data_dir = os.getenv("DATA_DIR", "./data")
    db_path = os.path.join(data_dir, "entrofeed.db")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, preview, content, url, published_at, feed_id
        FROM feed_entries
        ORDER BY published_at DESC
        LIMIT ?
    """, (limit,))

    entries = []
    for row in cursor.fetchall():
        entries.append({
            "id": row[0],
            "title": row[1],
            "preview": row[2],
            "content": row[3],
            "source": row[4],  # url column mapped to source
            "published_at": row[5],
            "feed_id": row[6],
            "tags": []  # Will be populated by scorer
        })

    conn.close()
    return entries


def calculate_statistics(scores: List[float]) -> Dict[str, float]:
    """Calculate statistical measures for score distribution.

    Args:
        scores: List of scores

    Returns:
        Dict with mean, median, std, percentiles
    """
    if not scores:
        return {}

    import statistics

    sorted_scores = sorted(scores)
    n = len(sorted_scores)

    return {
        "count": n,
        "mean": statistics.mean(scores),
        "median": statistics.median(scores),
        "std": statistics.stdev(scores) if n > 1 else 0.0,
        "min": min(scores),
        "max": max(scores),
        "p10": sorted_scores[int(n * 0.1)],
        "p25": sorted_scores[int(n * 0.25)],
        "p50": sorted_scores[int(n * 0.50)],
        "p75": sorted_scores[int(n * 0.75)],
        "p90": sorted_scores[int(n * 0.90)],
    }


def print_histogram(scores: List[float], bins: int = 10):
    """Print text-based histogram of score distribution.

    Args:
        scores: List of scores
        bins: Number of bins
    """
    if not scores:
        print("No scores to display")
        return

    min_score = min(scores)
    max_score = max(scores)
    bin_width = (max_score - min_score) / bins

    # Count scores in each bin
    bin_counts = [0] * bins
    for score in scores:
        bin_idx = min(int((score - min_score) / bin_width), bins - 1)
        bin_counts[bin_idx] += 1

    # Find max count for scaling
    max_count = max(bin_counts)
    scale = 50 / max_count if max_count > 0 else 1

    # Print histogram
    print("\nScore Distribution Histogram:")
    print("=" * 70)
    for i in range(bins):
        bin_start = min_score + i * bin_width
        bin_end = bin_start + bin_width
        bar_length = int(bin_counts[i] * scale)
        bar = "█" * bar_length
        print(f"{bin_start:.2f}-{bin_end:.2f} | {bar} ({bin_counts[i]})")
    print("=" * 70)


def print_dimension_breakdown(results: List[Dict[str, Any]]):
    """Print breakdown of scoring dimensions.

    Args:
        results: List of scored articles
    """
    dimensions = {
        "ontology_relevance": [],
        "authority_total": [],
        "impact_score": [],
        "recency_score": [],
        "graph_coefficient": [],
        "relevance_score": [],
    }

    for result in results:
        for dim in dimensions:
            if dim in result:
                dimensions[dim].append(result[dim])

    print("\n" + "=" * 70)
    print("DIMENSION BREAKDOWN")
    print("=" * 70)

    for dim_name, scores in dimensions.items():
        if not scores:
            continue
        stats = calculate_statistics(scores)
        print(f"\n{dim_name.upper()}:")
        print(f"  Mean: {stats['mean']:.4f}")
        print(f"  Median: {stats['median']:.4f}")
        print(f"  Std: {stats['std']:.4f}")
        print(f"  Range: [{stats['min']:.4f}, {stats['max']:.4f}]")
        print(f"  P25/P75: [{stats['p25']:.4f}, {stats['p75']:.4f}]")


def print_top_bottom_articles(results: List[Dict[str, Any]], n: int = 10):
    """Print top and bottom scored articles with explanations.

    Args:
        results: List of scored articles
        n: Number of articles to show
    """
    sorted_results = sorted(results, key=lambda x: x.get("total_score", 0), reverse=True)

    print("\n" + "=" * 70)
    print(f"TOP {n} SCORED ARTICLES")
    print("=" * 70)

    for i, article in enumerate(sorted_results[:n], 1):
        print(f"\n{i}. {article.get('title', 'No title')[:60]}")
        print(f"   Total Score: {article.get('total_score', 0):.4f}")
        print(f"   Ontology Relevance: {article.get('ontology_relevance', 0):.4f}")
        print(f"   Authority: {article.get('authority_total', 0):.4f}")
        print(f"   Impact: {article.get('impact_score', 0):.4f}")
        print(f"   Graph Coefficient: {article.get('graph_coefficient', 0):.4f}")
        if article.get('graph_matched_seeds'):
            print(f"   Matched Seeds: {', '.join(article['graph_matched_seeds'][:3])}")

    print("\n" + "=" * 70)
    print(f"BOTTOM {n} SCORED ARTICLES")
    print("=" * 70)

    for i, article in enumerate(sorted_results[-n:], 1):
        print(f"\n{i}. {article.get('title', 'No title')[:60]}")
        print(f"   Total Score: {article.get('total_score', 0):.4f}")
        print(f"   Ontology Relevance: {article.get('ontology_relevance', 0):.4f}")
        print(f"   Authority: {article.get('authority_total', 0):.4f}")
        print(f"   Impact: {article.get('impact_score', 0):.4f}")


def analyze_graph_coefficient_coverage(results: List[Dict[str, Any]]):
    """Analyze how many articles have non-zero graph coefficients.

    Args:
        results: List of scored articles
    """
    total = len(results)
    with_graph = sum(1 for r in results if r.get("graph_coefficient", 0) > 0)
    without_graph = total - with_graph

    print("\n" + "=" * 70)
    print("GRAPH COEFFICIENT COVERAGE")
    print("=" * 70)
    print(f"Total articles: {total}")
    print(f"With graph_coefficient > 0: {with_graph} ({with_graph/total*100:.1f}%)")
    print(f"With graph_coefficient = 0: {without_graph} ({without_graph/total*100:.1f}%)")

    # Breakdown by coefficient value
    exact_match = sum(1 for r in results if r.get("graph_coefficient", 0) >= 0.9)
    hop1_match = sum(1 for r in results if 0.4 <= r.get("graph_coefficient", 0) < 0.9)
    hop2_match = sum(1 for r in results if 0.1 <= r.get("graph_coefficient", 0) < 0.4)

    print("\nBreakdown:")
    print(f"  Exact match (≥0.9): {exact_match} ({exact_match/total*100:.1f}%)")
    print(f"  1-hop match (0.4-0.9): {hop1_match} ({hop1_match/total*100:.1f}%)")
    print(f"  2-hop match (0.1-0.4): {hop2_match} ({hop2_match/total*100:.1f}%)")


def main():
    """Main evaluation function."""
    print("=" * 70)
    print("ENTROFEED SCORING EVALUATION")
    print("=" * 70)

    # Load data
    print("\nLoading entries from database...")
    entries = load_entries_from_db(limit=20)  # Test with just 20 articles
    print(f"Loaded {len(entries)} entries")

    # Load user interests
    print("\nLoading user interests...")
    registry = get_ontology_registry()
    user_interests = registry.get_user_interests()
    print(f"Loaded {len(user_interests)} user interests")

    if not user_interests:
        print("\nWARNING: No user interests found. Scores will be low.")
        print("Run init_user_interests_from_file() first or add interests manually.")

    # Convert interests to dict format
    interests_dict = [
        {
            "name": i.tag.name,
            "category": i.tag.category.value,
            "priority": i.priority,
            "relevance_score": i.relevance_score,
            "synonyms": i.tag.synonyms,
        }
        for i in user_interests
    ]

    # Score all entries
    print("\nTagging and scoring entries...")
    from src.services.ontology import score_and_tag_articles, reset_article_tagger

    # Reset tagger to ensure it has __init__ called
    reset_article_tagger()

    results = score_and_tag_articles(entries, interests_dict)
    print(f"Tagged and scored {len(results)} entries")

    # Debug: Check first article's tags
    if results:
        first = results[0]
        print("\nDEBUG - First article tags:")
        for tag in first.get("tags", [])[:3]:
            print(f"  - {tag.get('name')}: QID={tag.get('wikidata_qid')}")
        print(f"  Graph coefficient: {first.get('graph_coefficient', 0)}")

    # Extract scores
    total_scores = [r.get("total_score", 0) for r in results]

    # Calculate statistics
    stats = calculate_statistics(total_scores)

    print("\n" + "=" * 70)
    print("OVERALL STATISTICS")
    print("=" * 70)
    print(f"Count: {stats['count']}")
    print(f"Mean: {stats['mean']:.4f}")
    print(f"Median: {stats['median']:.4f}")
    print(f"Std Dev: {stats['std']:.4f}")
    print(f"Min: {stats['min']:.4f}")
    print(f"Max: {stats['max']:.4f}")
    print("\nPercentiles:")
    print(f"  P10: {stats['p10']:.4f}")
    print(f"  P25: {stats['p25']:.4f}")
    print(f"  P50: {stats['p50']:.4f}")
    print(f"  P75: {stats['p75']:.4f}")
    print(f"  P90: {stats['p90']:.4f}")

    # Print histogram
    print_histogram(total_scores, bins=10)

    # Dimension breakdown
    print_dimension_breakdown(results)

    # Graph coefficient coverage
    analyze_graph_coefficient_coverage(results)

    # Top and bottom articles
    print_top_bottom_articles(results, n=10)

    print("\n" + "=" * 70)
    print("EVALUATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
