from DigitalTwinModule.models import TwinProfile, WeakNode


class WeakNodeDetector:
    WEAK_THRESHOLD = 0.6
    WEAK_THRESHOLD_PERCENT = 60.0
    MAX_RECOMMENDATIONS = 10

    def detect(self, profile: TwinProfile) -> list[WeakNode]:
        scores = [float(n.mastery_score or 0) for n in profile.knowledge_nodes]
        uses_percent_scale = float(profile.overall_mastery or 0) > 1 or any(
            score > 1 for score in scores
        )
        threshold = self.WEAK_THRESHOLD_PERCENT if uses_percent_scale else self.WEAK_THRESHOLD

        weak = [
            WeakNode(
                node_id=n.node_id,
                mastery_score=n.mastery_score,
                priority=0,
                resources=[],
            )
            for n in profile.knowledge_nodes
            if float(n.mastery_score or 0) < threshold
        ]
        weak.sort(key=lambda w: w.mastery_score)
        return weak[: self.MAX_RECOMMENDATIONS]
