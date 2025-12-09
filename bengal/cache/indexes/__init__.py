"""Built-in query indexes for common use cases."""

from __future__ import annotations

from bengal.cache.indexes.author_index import AuthorIndex
from bengal.cache.indexes.category_index import CategoryIndex
from bengal.cache.indexes.date_range_index import DateRangeIndex
from bengal.cache.indexes.section_index import SectionIndex

__all__ = ["SectionIndex", "AuthorIndex", "CategoryIndex", "DateRangeIndex"]
