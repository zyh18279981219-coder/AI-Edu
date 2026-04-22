"""Resource matching submodule."""

from KnowledgeGraph.src.resource_match.book_indexer import BookIndexer
from KnowledgeGraph.src.resource_match.settings import ResourceMatchSettings
from KnowledgeGraph.src.resource_match.video_matcher import VideoMatcher

__all__ = ["BookIndexer", "VideoMatcher", "ResourceMatchSettings"]
