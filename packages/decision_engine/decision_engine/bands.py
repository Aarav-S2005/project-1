"""Trust score band evaluator mapping trust scores and ReBAC status to gateway actions."""

import logging

from shared.config import get_settings
from shared.schemas.decision import DecisionAction

logger = logging.getLogger("decision_engine.bands")


class DecisionBandEvaluator:
    """Evaluates ReBAC authorization combined with dynamic trust scores into DecisionActions."""

    def __init__(
        self,
        allow_threshold: float | None = None,
        step_up_threshold: float | None = None,
        deny_threshold: float | None = None,
    ) -> None:
        settings = get_settings()
        self.allow_threshold = (
            allow_threshold if allow_threshold is not None else settings.band_threshold_narrow
        )
        self.step_up_threshold = (
            step_up_threshold if step_up_threshold is not None else settings.band_threshold_step_up
        )
        self.deny_threshold = (
            deny_threshold if deny_threshold is not None else settings.band_threshold_deny
        )

    def evaluate(
        self,
        rebac_allowed: bool,
        trust_score: float,
        narrow_threshold: float | None = None,
        step_up_threshold: float | None = None,
    ) -> tuple[DecisionAction, str]:
        """Map trust score and ReBAC permissionship to decision action and reason."""
        allow_th = narrow_threshold if narrow_threshold is not None else self.allow_threshold
        step_th = step_up_threshold if step_up_threshold is not None else self.step_up_threshold

        if not rebac_allowed:
            logger.info("Decision: DENY (ReBAC base permission check failed)")
            return DecisionAction.DENY, "rebac_permission_denied"

        if trust_score >= allow_th:
            logger.debug("Decision: ALLOW (trust_score=%.3f)", trust_score)
            return (
                DecisionAction.ALLOW,
                f"trust_score_{trust_score:.2f}_nominal_allow",
            )

        if trust_score >= step_th:
            logger.info(
                "Decision: NARROW (trust_score=%.3f in [%.2f, %.2f))",
                trust_score,
                step_th,
                allow_th,
            )
            return (
                DecisionAction.NARROW,
                f"trust_score_{trust_score:.2f}_degraded_narrow_applied",
            )

        if trust_score >= self.deny_threshold:
            logger.warning(
                "Decision: STEP_UP (trust_score=%.3f in [%.2f, %.2f))",
                trust_score,
                self.deny_threshold,
                self.step_up_threshold,
            )
            return (
                DecisionAction.STEP_UP,
                f"trust_score_{trust_score:.2f}_suspicious_step_up_required",
            )

        logger.warning(
            "Decision: DENY (trust_score=%.3f below critical threshold %.2f)",
            trust_score,
            self.deny_threshold,
        )
        return (
            DecisionAction.DENY,
            f"trust_score_{trust_score:.2f}_critical_denied",
        )
