"""Entropy Audit — evaluate LLM output uncertainty without logprobs.

Maps to the Harness paper's "熵审计" responsibility: assess the
uncertainty/entropy of model-generated content and trigger fallback
when outputs are too uncertain to be trusted.

Strategies (no logprobs needed):
- Lexical diversity (type-token ratio)
- Semantic coherence (sentence ngram overlap)
- Structural consistency (JSON validity, schema compliance)
- Repetition detection (ngram overlap)
- Confidence marker detection (hedging language)
"""

import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EntropyStrategy(str, Enum):
    LEXICAL_DIVERSITY = "lexical_diversity"
    SEMANTIC_COHERENCE = "semantic_coherence"
    STRUCTURAL_CONSISTENCY = "structural_consistency"
    REPETITION_DETECTION = "repetition_detection"
    CONFIDENCE_MARKERS = "confidence_markers"


class EntropyFactor(BaseModel):
    """A single entropy measurement from one strategy."""
    strategy: EntropyStrategy
    score: float = Field(default=0.0, ge=0.0, le=1.0)  # 0=low entropy(good), 1=high entropy(bad)
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    details: Dict[str, Any] = Field(default_factory=dict)


class EntropyReport(BaseModel):
    """Complete entropy audit report for a model response."""
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    factors: List[EntropyFactor] = Field(default_factory=list)
    exceeds_threshold: bool = False
    threshold: float = 0.7
    recommended_action: str = "proceed"  # "proceed" | "warn" | "fallback" | "retry"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EntropyAuditor:
    """Evaluates LLM output uncertainty using multiple heuristic strategies."""

    # ── Uncertainty / Certainty Markers ──────────────────────────────────

    UNCERTAINTY_MARKERS: List[str] = [
        "i think", "maybe", "perhaps", "might be", "could be", "possibly",
        "i'm not sure", "i am not sure", "unsure", "uncertain", "not confident",
        "i don't know", "i do not know", "not entirely sure", "it seems",
        "probably", "likely", "i assume", "i guess", "not clear",
        "approximately", "roughly", "more or less",
    ]

    CERTAINTY_MARKERS: List[str] = [
        "definitely", "certainly", "clearly", "without doubt", "confirmed",
        "i'm confident", "i am confident", "undoubtedly", "absolutely",
        "with certainty", "assuredly", "verified",
    ]

    # ── Strategy Weights ─────────────────────────────────────────────────

    DEFAULT_WEIGHTS = {
        EntropyStrategy.LEXICAL_DIVERSITY: 0.15,
        EntropyStrategy.SEMANTIC_COHERENCE: 0.25,
        EntropyStrategy.STRUCTURAL_CONSISTENCY: 0.25,
        EntropyStrategy.REPETITION_DETECTION: 0.20,
        EntropyStrategy.CONFIDENCE_MARKERS: 0.15,
    }

    def __init__(self, entropy_threshold: float = 0.7,
                 strategies: Optional[List[EntropyStrategy]] = None):
        self.entropy_threshold = entropy_threshold
        self.strategies = strategies or list(self.DEFAULT_WEIGHTS.keys())

    # ── Public API ───────────────────────────────────────────────────────

    def evaluate_response(self, response_text: str, context: Optional[Dict] = None) -> EntropyReport:
        """Evaluate the entropy/uncertainty of a model response.

        Returns an EntropyReport with aggregate score and per-factor breakdown.
        """
        if not response_text or not response_text.strip():
            return EntropyReport(
                score=1.0, exceeds_threshold=True,
                recommended_action="fallback",
            )

        context = context or {}
        strategy_methods = {
            EntropyStrategy.LEXICAL_DIVERSITY: self._lexical_diversity,
            EntropyStrategy.SEMANTIC_COHERENCE: self._semantic_coherence,
            EntropyStrategy.STRUCTURAL_CONSISTENCY: self._structural_consistency,
            EntropyStrategy.REPETITION_DETECTION: self._repetition_detection,
            EntropyStrategy.CONFIDENCE_MARKERS: self._confidence_markers,
        }

        factors: List[EntropyFactor] = []
        for strategy in self.strategies:
            if strategy in strategy_methods:
                factor = strategy_methods[strategy](response_text, context)
                factor.weight = self.DEFAULT_WEIGHTS.get(strategy, 1.0)
                factors.append(factor)

        # Weighted aggregate
        score = self._compute_aggregate_score(factors)

        # Determine action
        exceeds = score >= self.entropy_threshold
        if not exceeds:
            action = "proceed"
        elif score < 0.8:
            action = "warn"
        elif score < 0.95:
            action = "fallback"
        else:
            action = "retry"

        return EntropyReport(
            score=round(score, 3),
            factors=factors,
            exceeds_threshold=exceeds,
            threshold=self.entropy_threshold,
            recommended_action=action,
        )

    def is_safe(self, entropy_score: float) -> bool:
        """Check if an entropy score is below the threshold."""
        return entropy_score < self.entropy_threshold

    # ── Strategy Implementations ─────────────────────────────────────────

    def _lexical_diversity(self, text: str, context: Optional[Dict] = None) -> EntropyFactor:
        """Type-Token Ratio: higher TTR = more unique words = more unpredictable.

        Adjusts for text length to avoid penalizing short texts unfairly.
        Score: 1.0 - corrected_TTR (so high diversity → high entropy).
        """
        tokens = re.findall(r'\b\w+\b', text.lower())
        if not tokens:
            return EntropyFactor(strategy=EntropyStrategy.LEXICAL_DIVERSITY, score=1.0,
                                details={"error": "no tokens found"})
        total = len(tokens)
        unique = len(set(tokens))
        raw_ttr = unique / total

        # Correct for short text (Carroll's correction): TTR_corrected = unique / sqrt(2 * total)
        if total < 10:
            corrected_ttr = unique / total  # Short texts get raw TTR
        else:
            corrected_ttr = unique / math.sqrt(2 * total)

        # High diversity = high entropy; bounded to [0, 1]
        entropy_score = min(1.0, max(0.0, 1.0 - corrected_ttr))

        return EntropyFactor(strategy=EntropyStrategy.LEXICAL_DIVERSITY,
                            score=round(entropy_score, 3),
                            details={"total_tokens": total, "unique_tokens": unique,
                                     "raw_ttr": round(raw_ttr, 3), "corrected_ttr": round(corrected_ttr, 3)})

    def _semantic_coherence(self, text: str, context: Optional[Dict] = None) -> EntropyFactor:
        """Measure sentence-to-sentence coherence via bigram overlap.

        Low overlap between adjacent sentences suggests disjointed
        thinking → high entropy.
        """
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if len(s.strip().split()) > 2]
        if len(sentences) < 2:
            return EntropyFactor(strategy=EntropyStrategy.SEMANTIC_COHERENCE, score=0.3,
                                details={"sentence_count": len(sentences), "note": "insufficient sentences"})

        overlaps = []
        for i in range(len(sentences) - 1):
            s1_bigrams = set(zip(sentences[i].split(), sentences[i].split()[1:]))
            s2_bigrams = set(zip(sentences[i + 1].split(), sentences[i + 1].split()[1:]))
            if not s1_bigrams or not s2_bigrams:
                overlaps.append(0.0)
            else:
                overlaps.append(len(s1_bigrams & s2_bigrams) / len(s1_bigrams | s2_bigrams))

        avg_overlap = sum(overlaps) / len(overlaps) if overlaps else 0.0
        # Low overlap → high entropy
        entropy_score = max(0.0, 1.0 - avg_overlap)

        return EntropyFactor(strategy=EntropyStrategy.SEMANTIC_COHERENCE,
                            score=round(entropy_score, 3),
                            details={"sentence_count": len(sentences),
                                     "avg_overlap": round(avg_overlap, 3),
                                     "min_overlap": round(min(overlaps), 3)})

    def _structural_consistency(self, text: str, context: Optional[Dict] = None) -> EntropyFactor:
        """Check if the output has consistent, parseable structure.

        Tries JSON parsing — valid JSON with expected structure = low entropy.
        Non-JSON gets scored based on markdown/structural coherence.
        """
        # Try to parse as JSON
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            if len(lines) > 2:
                cleaned = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
            else:
                cleaned = cleaned.strip("`").strip()

        try:
            parsed = json.loads(cleaned)
            # Valid JSON — check for expected keys if provided
            expected_keys = (context or {}).get("expected_keys", [])
            if expected_keys:
                if isinstance(parsed, dict):
                    missing = [k for k in expected_keys if k not in parsed]
                    extra = [k for k in parsed if k not in expected_keys]
                    completeness = len(expected_keys) and (len(expected_keys) - len(missing)) / len(expected_keys) or 1.0
                    noise = len(extra) / max(len(expected_keys), 1)
                    score = 1.0 - (completeness * (1.0 - noise))
                else:
                    score = 0.5  # JSON but not dict
            else:
                score = 0.1  # Valid JSON, no schema to check — low entropy
        except (json.JSONDecodeError, ValueError):
            # Non-JSON — check for structural markers
            has_headers = bool(re.search(r'#{1,4}\s', text))
            has_lists = bool(re.search(r'^\s*[-*+]\s|\d+\.\s', text, re.MULTILINE))
            has_paragraphs = len(text.split('\n\n')) > 1

            structural_score = (has_headers * 0.4 + has_lists * 0.3 + has_paragraphs * 0.3)
            score = max(0.0, 1.0 - structural_score)  # High structure → low entropy

        return EntropyFactor(strategy=EntropyStrategy.STRUCTURAL_CONSISTENCY,
                            score=round(min(1.0, max(0.0, score)), 3),
                            details={"structure_type": "json" if 'parsed' in dir() else "text",
                                     "well_structured": score < 0.5})

    def _repetition_detection(self, text: str, context: Optional[Dict] = None) -> EntropyFactor:
        """Detect excessive repetition indicating degraded generation.

        Uses ngram (n=3,4) overlap analysis.
        """
        tokens = text.lower().split()
        if len(tokens) < 6:
            return EntropyFactor(strategy=EntropyStrategy.REPETITION_DETECTION, score=0.5,
                                details={"note": "text too short for repetition analysis"})

        repetition_scores = []
        for n in [3, 4]:
            if len(tokens) < n * 2:
                continue
            ngrams = [tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]
            ngram_counts = Counter(ngrams)
            total_ngrams = len(ngrams)
            if total_ngrams == 0:
                continue
            # Fraction of ngrams that appear more than once
            repeated = sum(c for _, c in ngram_counts.items() if c > 1)
            repetition_scores.append(repeated / total_ngrams)

        avg_repetition = sum(repetition_scores) / len(repetition_scores) if repetition_scores else 0.0
        # Clamp: above 0.5 repetition = very high entropy
        entropy_score = min(1.0, avg_repetition * 2.0)

        return EntropyFactor(strategy=EntropyStrategy.REPETITION_DETECTION,
                            score=round(entropy_score, 3),
                            details={"ngram_repetition_rate": round(avg_repetition, 3),
                                     "n_checked": len(repetition_scores)})

    def _confidence_markers(self, text: str, context: Optional[Dict] = None) -> EntropyFactor:
        """Detect hedging/uncertainty markers vs certainty markers.

        Higher ratio of uncertain → certain markers = higher entropy.
        """
        lower = text.lower()
        uncertain_count = sum(1 for m in self.UNCERTAINTY_MARKERS if m in lower)
        certain_count = sum(1 for m in self.CERTAINTY_MARKERS if m in lower)
        total = uncertain_count + certain_count

        if total == 0:
            # No markers either way — neutral
            return EntropyFactor(strategy=EntropyStrategy.CONFIDENCE_MARKERS, score=0.4,
                                details={"uncertain_count": 0, "certain_count": 0,
                                         "note": "no confidence markers detected"})

        score = uncertain_count / total
        return EntropyFactor(strategy=EntropyStrategy.CONFIDENCE_MARKERS,
                            score=round(score, 3),
                            details={"uncertain_count": uncertain_count,
                                     "certain_count": certain_count,
                                     "ratio": round(score, 3)})

    # ── Aggregate ────────────────────────────────────────────────────────

    def _compute_aggregate_score(self, factors: List[EntropyFactor]) -> float:
        """Weighted average of all factor scores."""
        if not factors:
            return 0.5
        weighted_sum = sum(f.score * f.weight for f in factors)
        total_weight = sum(f.weight for f in factors)
        if total_weight == 0:
            return 0.5
        return weighted_sum / total_weight
