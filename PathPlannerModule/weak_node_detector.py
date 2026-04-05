from DigitalTwinModule.models import TwinProfile, WeakNode


class WeakNodeDetector:
    WEAK_THRESHOLD = 60.0

    def detect(self, profile: TwinProfile) -> list[WeakNode]:
        """返回 mastery_score < 60 的节点，转换为 WeakNode，按 mastery_score 升序排列。"""
        weak = [
            WeakNode(
                node_id=n.node_id,
                mastery_score=n.mastery_score,
                priority=0,  # priority 由 PathPlannerAgent 分配
                resources=[]
            )
            for n in profile.knowledge_nodes
            if n.mastery_score < self.WEAK_THRESHOLD
        ]
        weak.sort(key=lambda w: w.mastery_score)
        return weak
