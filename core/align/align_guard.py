"""Alignment Guard Module

Provides safety and alignment checking for agent outputs and actions.
Implements content filtering, policy enforcement, and ethical boundary checks.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ViolationSeverity(Enum):
    """Severity level of an alignment violation."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Violation:
    """Represents an alignment violation."""

    rule_id: str
    message: str
    severity: ViolationSeverity
    category: str
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GuardResult:
    """Result of an alignment guard check."""

    allowed: bool
    violations: List[Violation] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    modified_output: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AlignmentRule:
    """Base class for alignment rules."""

    def __init__(self, rule_id: str, category: str, severity: ViolationSeverity):
        self.rule_id = rule_id
        self.category = category
        self.severity = severity

    def check(self, content: str, context: Dict[str, Any]) -> Optional[Violation]:
        """Check content against this rule. Returns Violation if violated, None otherwise."""
        raise NotImplementedError


class ContentSafetyRule(AlignmentRule):
    """Rule for detecting unsafe or harmful content."""

    BLOCKED_PATTERNS = [
        (r"(?i)\b(exploit|vulnerability)\s+in\s+(order\s+to|so\s+that|to)\s+(hack|attack|steal|destroy)\b", ViolationSeverity.CRITICAL),
        (r"(?i)\b(generate|create|write)\s+(malware|ransomware|virus|trojan|worm)\b", ViolationSeverity.CRITICAL),
        (r"(?i)\b(how\s+to|steps?\s+to|guide\s+to)\s+(hack|crack|phish|ddos|spoof)\b", ViolationSeverity.HIGH),
        (r"(?i)\b(buy|sell|trade)\s+(drugs?|weapons?|stolen)\b", ViolationSeverity.CRITICAL),
        (r"(?i)\bpersonal\s+(information|data)\s+(of|about)\s+(someone|others?|people)\b", ViolationSeverity.HIGH),
    ]

    def __init__(self):
        super().__init__("content_safety", "safety", ViolationSeverity.HIGH)

    def check(self, content: str, context: Dict[str, Any]) -> Optional[Violation]:
        for pattern, severity in self.BLOCKED_PATTERNS:
            if re.search(pattern, content):
                return Violation(
                    rule_id=self.rule_id,
                    message=f"Content safety violation detected: matched blocked pattern",
                    severity=severity,
                    category=self.category,
                    context={"matched_pattern": pattern},
                )
        return None


class PIIRule(AlignmentRule):
    """Rule for detecting potential PII (Personally Identifiable Information) leakage."""

    PII_PATTERNS = [
        (r"\b\d{3}-\d{2}-\d{4}\b", "SSN pattern"),
        (r"\b\d{16}\b", "Credit card number pattern"),
        (r"\b\d{3}-\d{3}-\d{4}\b", "Phone number pattern"),
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "Email address"),
    ]

    def __init__(self):
        super().__init__("pii_detection", "privacy", ViolationSeverity.HIGH)

    def check(self, content: str, context: Dict[str, Any]) -> Optional[Violation]:
        for pattern, label in self.PII_PATTERNS:
            match = re.search(pattern, content)
            if match:
                return Violation(
                    rule_id=self.rule_id,
                    message=f"Potential PII detected: {label}",
                    severity=self.severity,
                    category=self.category,
                    context={"pii_type": label},
                )
        return None


class PromptInjectionRule(AlignmentRule):
    """Rule for detecting prompt injection attempts."""

    INJECTION_PATTERNS = [
        r"(?i)\b(ignore|forget|disregard)\s+(all\s+)?(previous|above|prior|earlier)\s+(instructions?|prompts?|messages?|directives?)\b",
        r"(?i)\byou\s+are\s+now\s+(DAN|jailbroken|unshackled|unfiltered)\b",
        r"(?i)\byour\s+new\s+(role|identity|name|purpose)\s+is\b",
        r"(?i)\bpretend\s+(you\s+are|to\s+be|that)\b",
        r"(?i)\b(system\s*:\s*|system\s+prompt\s*:|you\s+must\s+(always\s+)?(respond|reply|answer|say))\b",
    ]

    def __init__(self):
        super().__init__("prompt_injection", "security", ViolationSeverity.HIGH)

    def check(self, content: str, context: Dict[str, Any]) -> Optional[Violation]:
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, content):
                return Violation(
                    rule_id=self.rule_id,
                    message="Potential prompt injection detected",
                    severity=self.severity,
                    category=self.category,
                    context={"matched_pattern": pattern},
                )
        return None


class CodeExecutionRule(AlignmentRule):
    """Rule for checking safety of code execution requests."""

    DANGEROUS_CODE_PATTERNS = [
        r"\bimport\s+(os|subprocess|sys|shutil|ctypes)\b",
        r"\bos\.(system|popen|remove|rmdir|unlink)\b",
        r"\bsubprocess\.(run|Popen|call|check_output)\b",
        r"\b__import__\s*\(",
        r"\beval\s*\(",
        r"\bexec\s*\(",
        r"\bopen\s*\([^)]*['\"][wa]",
        r"\bshutil\.(rmtree|move|copy2?)\b",
    ]

    def __init__(self):
        super().__init__("code_execution_safety", "safety", ViolationSeverity.MEDIUM)

    def check(self, content: str, context: Dict[str, Any]) -> Optional[Violation]:
        for pattern in self.DANGEROUS_CODE_PATTERNS:
            if re.search(pattern, content):
                return Violation(
                    rule_id=self.rule_id,
                    message=f"Potentially dangerous code detected",
                    severity=self.severity,
                    category=self.category,
                    context={"matched_pattern": pattern},
                )
        return None


class AlignGuard:
    """Main alignment guard that orchestrates all safety and alignment checks.

    Applies a pipeline of rules to check agent inputs and outputs for
    safety, privacy, and policy compliance issues.
    """

    def __init__(self, enabled: bool = True, strict_mode: bool = False):
        """
        Initialize the alignment guard.

        Args:
            enabled: Whether the guard is active
            strict_mode: If True, even LOW severity violations block execution
        """
        self.enabled = enabled
        self.strict_mode = strict_mode
        self.rules: List[AlignmentRule] = [
            ContentSafetyRule(),
            PIIRule(),
            PromptInjectionRule(),
            CodeExecutionRule(),
        ]
        self._violation_history: List[Violation] = []
        self._max_history = 1000

    def register_rule(self, rule: AlignmentRule):
        """Register a custom alignment rule."""
        self.rules.append(rule)

    def check_input(self, content: str, context: Optional[Dict[str, Any]] = None) -> GuardResult:
        """
        Check user input for alignment violations.

        Args:
            content: The input content to check
            context: Additional context (user info, session data, etc.)

        Returns:
            GuardResult with pass/fail status and any violations
        """
        return self._run_checks(content, context or {})

    def check_output(self, content: str, context: Optional[Dict[str, Any]] = None) -> GuardResult:
        """
        Check agent output for alignment violations before sending to user.

        Args:
            content: The output content to check
            context: Additional context

        Returns:
            GuardResult with pass/fail status and any violations
        """
        return self._run_checks(content, context or {})

    def check_code(self, code: str, context: Optional[Dict[str, Any]] = None) -> GuardResult:
        """
        Check code for safety before execution.

        Args:
            code: The code to check
            context: Additional context (sandbox info, etc.)

        Returns:
            GuardResult with pass/fail status and any violations
        """
        ctx = context or {}
        ctx["content_type"] = "code"
        return self._run_checks(code, ctx)

    def _run_checks(self, content: str, context: Dict[str, Any]) -> GuardResult:
        """
        Run all registered rules against the content.

        Args:
            content: Content to check
            context: Context dictionary

        Returns:
            GuardResult with aggregated results
        """
        if not self.enabled:
            return GuardResult(allowed=True)

        violations = []
        warnings = []

        for rule in self.rules:
            try:
                violation = rule.check(content, context)
                if violation:
                    violations.append(violation)
                    self._violation_history.append(violation)
            except Exception as e:
                warnings.append(f"Rule {rule.rule_id} failed to execute: {str(e)}")

        # Trim history
        if len(self._violation_history) > self._max_history:
            self._violation_history = self._violation_history[-self._max_history:]

        # Determine if content is allowed
        if not violations:
            return GuardResult(allowed=True, warnings=warnings)

        # Block if any CRITICAL or HIGH severity violation
        blocking_violations = [v for v in violations if v.severity in (ViolationSeverity.CRITICAL, ViolationSeverity.HIGH)]
        if self.strict_mode:
            blocking_violations = violations  # In strict mode, all violations block

        allowed = len(blocking_violations) == 0

        return GuardResult(
            allowed=allowed,
            violations=violations,
            warnings=warnings,
            metadata={
                "total_rules": len(self.rules),
                "violations_found": len(violations),
                "strict_mode": self.strict_mode,
            },
        )

    def get_violation_statistics(self) -> Dict[str, Any]:
        """Get statistics about past violations."""
        if not self._violation_history:
            return {"total_violations": 0}

        category_counts: Dict[str, int] = {}
        severity_counts: Dict[str, int] = {}

        for v in self._violation_history:
            category_counts[v.category] = category_counts.get(v.category, 0) + 1
            severity_counts[v.severity.value] = severity_counts.get(v.severity.value, 0) + 1

        return {
            "total_violations": len(self._violation_history),
            "by_category": category_counts,
            "by_severity": severity_counts,
        }

    def reset_history(self):
        """Clear violation history."""
        self._violation_history.clear()

    def enable(self):
        """Enable the guard."""
        self.enabled = True

    def disable(self):
        """Disable the guard."""
        self.enabled = False
