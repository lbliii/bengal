"""
Cacheable Protocol - Type-safe cache contracts for Bengal.

This module defines a Protocol that cacheable types can implement to ensure
type-safe serialization and deserialization. Any type that needs to be cached
to disk should implement this protocol.

The protocol enforces:
- Consistent serialization pattern (to_cache_dict/from_cache_dict)
- Type-safe round-trip (obj == T.from_cache_dict(obj.to_cache_dict()))
- JSON-compatible serialization (str, int, float, bool, None, list, dict)
- Compile-time validation via mypy

Design Philosophy:
    Unlike PageCore (which solves the live/cache/proxy split problem), the
    Cacheable protocol provides a lightweight contract for ANY type that needs
    caching, without requiring inheritance or base classes.

    Use Cacheable when:
    - Type needs to be persisted to disk (cache files, indexes)
    - Type should be serialized consistently across codebase
    - Type-safety for serialization is desired
    - No three-way split (live/cache/proxy) exists

    Use *Core base class (like PageCore) when:
    - Type has three-way split (Live → Cache → Proxy)
    - Templates access many properties (lazy loading matters)
    - Manual sync between representations causes bugs

See Also:
    - bengal/cache/cache_store.py - Generic cache helper using this protocol
    - bengal/core/page/page_core.py - PageCore (uses protocol)
    - bengal/cache/taxonomy_index.py - TagEntry (uses protocol)
    - architecture/cache.md - Cache architecture documentation
    - plan/active/rfc-cacheable-protocol.md - Design rationale
"""

from __future__ import annotations

from typing import Any, Protocol, TypeVar, runtime_checkable

# TypeVar bound to Cacheable for generic return types
T = TypeVar("T", bound="Cacheable")


@runtime_checkable
class Cacheable(Protocol):
    """
    Protocol for types that can be cached to disk.

    Types implementing this protocol can be automatically serialized to JSON
    and deserialized, with type checker validation.

    Contract Requirements:
        1. JSON Primitives Only: to_cache_dict() must return only JSON-serializable
           types: str, int, float, bool, None, list, dict.

        2. Type Conversion: Complex types must be converted:
           - datetime → ISO-8601 string (via datetime.isoformat())
           - Path → str (via str(path))
           - set → sorted list (for stability)

        3. No Object References: Never serialize live objects (Page, Section, Asset).
           Use stable identifiers (usually string paths) instead.

        4. Round-trip Invariant: T.from_cache_dict(obj.to_cache_dict()) must
           reconstruct an equivalent object (== by fields).

        5. Stable Keys: Field names in to_cache_dict() are the contract.
           Adding/removing fields requires version bump in cache file.

    Runtime Validation:
        The @runtime_checkable decorator allows isinstance() checks:

            if isinstance(obj, Cacheable):
                data = obj.to_cache_dict()

        However, static type checking via mypy is the primary validation method.

    Example (Simple Type):
        @dataclass
        class TagEntry(Cacheable):
            tag_slug: str
            tag_name: str
            page_paths: list[str]
            updated_at: str

            def to_cache_dict(self) -> dict[str, Any]:
                return {
                    'tag_slug': self.tag_slug,
                    'tag_name': self.tag_name,
                    'page_paths': self.page_paths,
                    'updated_at': self.updated_at,
                }

            @classmethod
            def from_cache_dict(cls, data: dict[str, Any]) -> 'TagEntry':
                return cls(
                    tag_slug=data['tag_slug'],
                    tag_name=data['tag_name'],
                    page_paths=data['page_paths'],
                    updated_at=data['updated_at'],
                )

    Example (Complex Type with datetime and Path):
        @dataclass
        class PageCore(Cacheable):
            source_path: str  # Already stored as string
            title: str
            date: datetime | None
            tags: list[str]

            def to_cache_dict(self) -> dict[str, Any]:
                return {
                    'source_path': self.source_path,
                    'title': self.title,
                    'date': self.date.isoformat() if self.date else None,
                    'tags': self.tags,
                }

            @classmethod
            def from_cache_dict(cls, data: dict[str, Any]) -> 'PageCore':
                return cls(
                    source_path=data['source_path'],
                    title=data['title'],
                    date=datetime.fromisoformat(data['date']) if data['date'] else None,
                    tags=data['tags'],
                )

    Example (Type with Object References):
        # WRONG: Don't serialize object references
        @dataclass
        class Page(Cacheable):
            section: Section  # ❌ Object reference

            def to_cache_dict(self) -> dict[str, Any]:
                return {'section': self.section}  # ❌ Not JSON-serializable!

        # CORRECT: Use stable identifier (path string)
        @dataclass
        class PageCore(Cacheable):
            section: str | None  # ✅ Path string

            def to_cache_dict(self) -> dict[str, Any]:
                return {'section': self.section}  # ✅ JSON-serializable

    Serialization Guidelines:
        datetime → ISO-8601 string:
            to_cache_dict: self.date.isoformat() if self.date else None
            from_cache_dict: datetime.fromisoformat(data['date']) if data['date'] else None

        Path → str:
            to_cache_dict: str(self.path)
            from_cache_dict: Path(data['path'])

        set → sorted list:
            to_cache_dict: sorted(list(self.tags))
            from_cache_dict: set(data['tags'])

        Optional fields:
            to_cache_dict: self.optional_field  # None is JSON-serializable
            from_cache_dict: data.get('optional_field')  # Default to None

    Testing:
        Every Cacheable type should have a roundtrip test:

            def test_roundtrip(self):
                obj = MyType(field1="value", field2=42)
                data = obj.to_cache_dict()
                loaded = MyType.from_cache_dict(data)
                assert obj == loaded

    Performance:
        - Protocol has zero runtime overhead (structural typing)
        - isinstance() check is O(1) attribute lookup
        - Serialization speed depends on implementation (~10µs for typical objects)

    See Also:
        - bengal/cache/cache_store.py - Generic cache storage using this protocol
        - tests/unit/test_cacheable.py - Protocol validation tests
    """

    def to_cache_dict(self) -> dict[str, Any]:
        """
        Serialize to cache-friendly dictionary.

        Must return JSON-serializable types only:
        - Primitives: str, int, float, bool, None
        - Collections: list, dict (containing primitives)

        Complex types must be converted:
        - datetime → ISO-8601 string (datetime.isoformat())
        - Path → string (str(path))
        - set → sorted list (for stability)

        No object references: Never serialize live objects (Page, Section).
        Use stable identifiers (paths as strings) instead.

        Returns:
            Dictionary suitable for JSON serialization

        Example:
            >>> @dataclass
            ... class TagEntry(Cacheable):
            ...     tag_slug: str
            ...     page_paths: list[str]
            ...
            ...     def to_cache_dict(self) -> dict[str, Any]:
            ...         return {
            ...             'tag_slug': self.tag_slug,
            ...             'page_paths': self.page_paths,
            ...         }
        """
        ...

    @classmethod
    def from_cache_dict(cls: type[T], data: dict[str, Any]) -> T:
        """
        Deserialize from cache dictionary.

        Must be inverse of to_cache_dict():
            assert obj == cls.from_cache_dict(obj.to_cache_dict())

        Handle type conversion:
        - ISO-8601 string → datetime (datetime.fromisoformat())
        - string → Path (Path())
        - list → set (set())

        Handle missing/optional fields:
        - Use data.get('field', default_value)
        - Preserve None for optional fields

        Args:
            data: Dictionary from cache (JSON-deserialized)

        Returns:
            Reconstructed instance

        Example:
            >>> @classmethod
            ... def from_cache_dict(cls, data: dict[str, Any]) -> 'TagEntry':
            ...     return cls(
            ...         tag_slug=data['tag_slug'],
            ...         page_paths=data['page_paths'],
            ...     )
        """
        ...
