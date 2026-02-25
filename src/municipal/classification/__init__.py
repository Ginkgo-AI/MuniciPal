"""Data classification module for Munici-Pal.

Provides rule-based classification of municipal data per REFERENCE.md Section 3.
"""

from municipal.classification.rules import ClassificationEngine, classify

__all__ = ["ClassificationEngine", "classify"]
