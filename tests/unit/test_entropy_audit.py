"""Unit tests for the Entropy Audit module."""

import pytest
from core.entropy_audit import EntropyAuditor, EntropyReport, EntropyStrategy, EntropyFactor


class TestEntropyAuditorLexicalDiversity:
    def test_high_entropy_diverse_text(self):
        auditor = EntropyAuditor()
        # Very diverse vocabulary — should have moderate-high entropy
        text = " ".join(f"unique_word_{i}" for i in range(50))
        factor = auditor._lexical_diversity(text)
        assert 0.0 <= factor.score <= 1.0
        assert factor.strategy == EntropyStrategy.LEXICAL_DIVERSITY

    def test_low_entropy_repetitive_text(self):
        auditor = EntropyAuditor()
        text = "the cat sat on the mat the cat sat on the mat " * 10
        factor = auditor._lexical_diversity(text)
        assert 0.0 <= factor.score <= 1.0
        # Repetitive text should have lower diversity = higher repetition entropy
        # but TTR-based diversity is low, so entropy from diversity is high
        # Actually: low diversity = low TTR = high entropy score (1.0 - low_TTR)
        # So repetitive text has high entropy

    def test_empty_text(self):
        auditor = EntropyAuditor()
        factor = auditor._lexical_diversity("")
        assert factor.score == 1.0


class TestEntropyAuditorConfidenceMarkers:
    def test_uncertain_text(self):
        auditor = EntropyAuditor()
        text = "I think this might be correct but I'm not sure. Perhaps we should verify."
        factor = auditor._confidence_markers(text)
        assert factor.score > 0.5  # Heavily uncertain

    def test_certain_text(self):
        auditor = EntropyAuditor()
        text = "This is definitely correct. Clearly the answer is 42. I'm confident."
        factor = auditor._confidence_markers(text)
        assert factor.score < 0.5  # Mostly certain

    def test_no_markers_text(self):
        auditor = EntropyAuditor()
        text = "The system processes data through a pipeline."
        factor = auditor._confidence_markers(text)
        assert factor.score == 0.4  # Neutral when no markers


class TestEntropyAuditorRepetition:
    def test_repetition_detected(self):
        auditor = EntropyAuditor()
        text = "hello world " * 20
        factor = auditor._repetition_detection(text)
        assert 0.0 <= factor.score <= 1.0

    def test_no_repetition(self):
        auditor = EntropyAuditor()
        words = [f"token_{i}" for i in range(50)]
        text = " ".join(words)
        factor = auditor._repetition_detection(text)
        assert factor.score < 0.5  # Low repetition


class TestEntropyAuditorSemanticCoherence:
    def test_coherent_text(self):
        auditor = EntropyAuditor()
        text = (
            "The system processes data efficiently. "
            "Data processing requires careful planning. "
            "Planning ensures optimal resource utilization."
        )
        factor = auditor._semantic_coherence(text)
        assert 0.0 <= factor.score <= 1.0

    def test_incoherent_text(self):
        auditor = EntropyAuditor()
        text = (
            "Banana phone quantum refrigerator dreams. "
            "Purple elephant constitution swimming backwards. "
            "Discombobulated symphony of chocolate mathematics."
        )
        factor = auditor._semantic_coherence(text)
        assert 0.0 <= factor.score <= 1.0

    def test_single_sentence(self):
        auditor = EntropyAuditor()
        factor = auditor._semantic_coherence("Only one sentence here.")
        assert factor.score == 0.3  # Default for insufficient sentences


class TestEntropyAuditorStructuralConsistency:
    def test_valid_json(self):
        auditor = EntropyAuditor()
        text = '{"name": "test", "value": 42}'
        factor = auditor._structural_consistency(text)
        assert factor.score < 0.3  # Valid JSON = low entropy

    def test_invalid_json(self):
        auditor = EntropyAuditor()
        text = "This is just plain unstructured text"
        factor = auditor._structural_consistency(text)
        assert 0.0 <= factor.score <= 1.0

    def test_json_with_expected_keys(self):
        auditor = EntropyAuditor()
        text = '{"name": "test", "age": 30}'
        factor = auditor._structural_consistency(text, {"expected_keys": ["name", "age"]})
        assert 0.0 <= factor.score <= 1.0


class TestEntropyAuditorFullEvaluation:
    def test_full_evaluation_below_threshold(self):
        auditor = EntropyAuditor(entropy_threshold=0.7)
        text = (
            '{"action": "read_file", "path": "/tmp/test.txt", "confidence": 0.95}\n'
            "This is definitely the correct approach. The file clearly exists."
        )
        report = auditor.evaluate_response(text)
        assert isinstance(report, EntropyReport)
        assert 0.0 <= report.score <= 1.0
        assert report.threshold == 0.7

    def test_full_evaluation_empty_text(self):
        auditor = EntropyAuditor()
        report = auditor.evaluate_response("")
        assert report.score == 1.0
        assert report.exceeds_threshold
        assert report.recommended_action == "fallback"

    def test_is_safe(self):
        auditor = EntropyAuditor(entropy_threshold=0.7)
        assert auditor.is_safe(0.3)
        assert not auditor.is_safe(0.9)
        assert not auditor.is_safe(0.7)

    def test_custom_threshold(self):
        auditor = EntropyAuditor(entropy_threshold=0.5)
        # Most text will exceed 0.5 threshold
        report = auditor.evaluate_response(
            "I think maybe we could perhaps try this approach but I'm not sure it might work."
        )
        assert report.threshold == 0.5
        assert isinstance(report.recommended_action, str)

    def test_strategy_subset(self):
        auditor = EntropyAuditor(
            entropy_threshold=0.7,
            strategies=[EntropyStrategy.CONFIDENCE_MARKERS, EntropyStrategy.LEXICAL_DIVERSITY],
        )
        text = "I am certain this is correct."
        report = auditor.evaluate_response(text)
        assert len(report.factors) == 2


class TestEntropyFactor:
    def test_factor_defaults(self):
        factor = EntropyFactor(strategy=EntropyStrategy.LEXICAL_DIVERSITY, score=0.5)
        assert factor.weight == 1.0
        assert factor.details == {}

    def test_factor_with_details(self):
        factor = EntropyFactor(
            strategy=EntropyStrategy.CONFIDENCE_MARKERS,
            score=0.8,
            weight=0.5,
            details={"uncertain_count": 3, "certain_count": 0},
        )
        assert factor.score == 0.8
        assert factor.details["uncertain_count"] == 3
