"""Convenience exports for the quiz module.

Keep these exports lazy so lightweight submodules can be imported by database
code without pulling in quiz operations, learning plans, and database factories.
"""

__all__ = [
    "generate_quiz",
    "prepare_quiz_questions",
    "generate_learning_plan_from_quiz",
    "Quiz_Agent",
]


def __getattr__(name):
    if name in {"generate_quiz", "prepare_quiz_questions", "generate_learning_plan_from_quiz"}:
        from . import quiz_operations

        return getattr(quiz_operations, name)
    if name == "Quiz_Agent":
        from .quiz_agent import Quiz_Agent

        return Quiz_Agent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
