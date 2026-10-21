"""Unified Decision Engine service coordinating ReBAC, score bands, and closed-loop feedback."""

import logging

import redis.asyncio as redis
from shared.schemas.decision import (
    ClosedLoopAction,
    DecisionAction,
    DecisionResult,
    EvaluationRequest,
)
from shared.schemas.trust import TrustScoreResult

from decision_engine.bands import DecisionBandEvaluator
from decision_engine.closed_loop import ClosedLoopManager
from decision_engine.policy.spicedb import SpiceDBClient

logger = logging.getLogger("decision_engine.service")


def parse_entity(entity: str) -> tuple[str, str]:
    """Parse entity string into (type, id), e.g. 'user:alice' -> ('user', 'alice')."""
    parts = entity.split(":", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f"Invalid entity format: '{entity}'. Expected 'type:id'.")
    return parts[0], parts[1]


class DecisionEngineService:
    """Evaluates requests by checking ReBAC permissions, applying trust bands,
    and executing closed-loop write-backs.
    """

    def __init__(
        self,
        spicedb_client: SpiceDBClient,
        redis_client: redis.Redis,
        evaluator: DecisionBandEvaluator | None = None,
        closed_loop: ClosedLoopManager | None = None,
    ) -> None:
        self.spicedb_client = spicedb_client
        self.redis_client = redis_client
        self.evaluator = evaluator or DecisionBandEvaluator()
        self.closed_loop = closed_loop or ClosedLoopManager(
            spicedb_client=self.spicedb_client,
            redis_client=self.redis_client,
        )

    async def evaluate(
        self,
        request: EvaluationRequest,
        trust_result: TrustScoreResult,
    ) -> DecisionResult:
        """Evaluate access authorization for an incoming request against trust score
        and ReBAC graph.
        """
        res_type, res_id = parse_entity(request.resource)
        sub_type, sub_id = parse_entity(request.subject)

        # 1. Base ReBAC check in SpiceDB
        rebac_allowed = self.spicedb_client.check_permission(
            resource_type=res_type,
            resource_id=res_id,
            permission=request.permission,
            subject_type=sub_type,
            subject_id=sub_id,
        )

        # 2. Check runtime parameter overrides from Redis
        narrow_th = None
        step_up_th = None
        narrow_ttl = None
        try:
            runtime_params = await self.redis_client.hgetall("trust:runtime_parameters")
            if runtime_params:
                if b"narrow_band_threshold" in runtime_params:
                    narrow_th = float(runtime_params[b"narrow_band_threshold"])
                if b"step_up_band_threshold" in runtime_params:
                    step_up_th = float(runtime_params[b"step_up_band_threshold"])
                if b"narrow_ttl_seconds" in runtime_params:
                    narrow_ttl = int(runtime_params[b"narrow_ttl_seconds"])
        except Exception as exc:
            logger.debug("Could not read runtime parameters from Redis: %s", exc)

        # 3. Decision Band Evaluation
        decision, reason = self.evaluator.evaluate(
            rebac_allowed=rebac_allowed,
            trust_score=trust_result.current_score,
            narrow_threshold=narrow_th,
            step_up_threshold=step_up_th,
        )

        # 4. Closed-Loop Feedback: if NARROW, write temporary restriction tuple to SpiceDB
        closed_loop_action: ClosedLoopAction | None = None
        if decision == DecisionAction.NARROW:
            closed_loop_action = await self.closed_loop.apply_narrow(
                resource_type=res_type,
                resource_id=res_id,
                subject_type=sub_type,
                subject_id=sub_id,
                ttl_seconds=narrow_ttl,
            )

        return DecisionResult(
            decision=decision,
            decision_reason=reason,
            rebac_allowed=rebac_allowed,
            trust_score=trust_result.current_score,
            trust_result=trust_result,
            closed_loop_action=closed_loop_action,
        )
