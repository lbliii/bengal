"""
DAG scheduler for the data-driven build pipeline.

Builds a directed acyclic graph from task ``requires`` / ``produces``
declarations and groups independent tasks into parallel execution
batches using a modified Kahn's algorithm.

Raises :class:`CyclicDependencyError` if the dependency graph contains
a cycle and :class:`MissingDependencyError` if a task requires a key
that no other task produces and that key is not in the initial context.
"""

from __future__ import annotations

from collections import defaultdict, deque

from bengal.orchestration.pipeline.task import BuildTask


class CyclicDependencyError(Exception):
    """Raised when the task DAG contains a cycle."""


class MissingDependencyError(Exception):
    """Raised when a required key is neither produced by a task nor in the initial context."""


class DuplicateProducerError(Exception):
    """Raised when two tasks declare the same ``produces`` key."""


class TaskScheduler:
    """
    Compute parallel execution batches from task declarations.

    The scheduler:

    1. Indexes every ``produces`` key to its owning task.
    2. Builds an adjacency graph (task A depends on task B if A requires
       a key that B produces).
    3. Validates there are no cycles (Kahn's algorithm will detect them).
    4. Groups tasks into *batches* -- within a batch every task is
       independent and can run in parallel.

    Args:
        tasks: Ordered list of :class:`BuildTask` declarations.
        initial_keys: Keys already available on the
            :class:`~bengal.orchestration.build_context.BuildContext`
            before the pipeline starts (e.g. ``"site"``, ``"options"``).
    """

    def __init__(
        self,
        tasks: list[BuildTask],
        initial_keys: frozenset[str] | None = None,
        task_durations_ms: dict[str, float] | None = None,
    ) -> None:
        self._tasks: dict[str, BuildTask] = {}
        for t in tasks:
            if t.name in self._tasks:
                msg = f"Duplicate task name: {t.name!r}"
                raise ValueError(msg)
            self._tasks[t.name] = t

        self._initial_keys = initial_keys or frozenset()
        self._task_durations_ms = task_durations_ms or {}
        self._batches: list[list[BuildTask]] = []
        self._validate_and_schedule()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def batches(self) -> list[list[BuildTask]]:
        """Execution batches in topological order."""
        return self._batches

    @property
    def batch_count(self) -> int:
        """Number of sequential batches."""
        return len(self._batches)

    @property
    def task_count(self) -> int:
        """Total number of registered tasks."""
        return len(self._tasks)

    def plan_for_outputs(self, target_keys: frozenset[str]) -> list[list[BuildTask]]:
        """
        Compute a minimal schedule that produces *target_keys*.

        This is a reverse-planning helper for "leaf-to-trunk" experiments:
        walk dependencies backwards from desired output keys to identify the
        minimal required task subgraph, then schedule that subgraph forward.

        Args:
            target_keys: Logical keys we want produced.

        Returns:
            Topologically sorted execution batches for the required subgraph.
            Returns an empty list when none of the targets are produced by tasks.
        """
        if not target_keys:
            return self._batches

        producers: dict[str, str] = {}
        for task in self._tasks.values():
            for key in task.produces:
                producers[key] = task.name

        needed_tasks: set[str] = set()
        keys_to_resolve = deque(target_keys)
        resolved_keys: set[str] = set()

        while keys_to_resolve:
            key = keys_to_resolve.popleft()
            if key in resolved_keys:
                continue
            resolved_keys.add(key)

            producer = producers.get(key)
            if producer is None or producer in needed_tasks:
                continue

            needed_tasks.add(producer)
            task = self._tasks[producer]
            for req in task.requires:
                if req not in self._initial_keys:
                    keys_to_resolve.append(req)

        if not needed_tasks:
            return []

        return self._schedule_subset(needed_tasks)

    def describe(self) -> str:
        """Return a human-readable summary of the schedule."""
        lines: list[str] = []
        for idx, batch in enumerate(self._batches):
            names = " | ".join(t.name for t in batch)
            parallel_hint = " (parallel)" if len(batch) > 1 else ""
            lines.append(f"Batch {idx}{parallel_hint}: {names}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _validate_and_schedule(self) -> None:
        """Build DAG, validate, and compute batches."""
        # 1. Build producer index:  key -> task name
        producers: dict[str, str] = {}
        for task in self._tasks.values():
            for key in task.produces:
                if key in producers:
                    raise DuplicateProducerError(
                        f"Key {key!r} produced by both "
                        f"{producers[key]!r} and {task.name!r}"
                    )
                producers[key] = task.name

        # 2. Validate every required key is satisfiable
        available = set(self._initial_keys)
        for task in self._tasks.values():
            available |= task.produces

        for task in self._tasks.values():
            missing = task.requires - available
            if missing:
                raise MissingDependencyError(
                    f"Task {task.name!r} requires {missing} but no task "
                    f"produces them and they are not in the initial context"
                )

        # 3. Build adjacency graph  (task -> set of task names it depends on)
        deps: dict[str, set[str]] = {name: set() for name in self._tasks}
        for task in self._tasks.values():
            for key in task.requires:
                if key in producers:
                    dep_name = producers[key]
                    if dep_name != task.name:
                        deps[task.name].add(dep_name)

        # 4. Kahn's algorithm with batch grouping
        in_degree: dict[str, int] = {name: len(d) for name, d in deps.items()}

        # Reverse adjacency: task -> tasks that depend on it
        dependents: dict[str, list[str]] = defaultdict(list)
        for name, dep_set in deps.items():
            for d in dep_set:
                dependents[d].append(name)

        critical_scores = self._compute_critical_scores(dependents)

        queue: deque[str] = deque(name for name, degree in in_degree.items() if degree == 0)

        scheduled = 0
        while queue:
            # Everything in the current queue has in-degree 0 → one batch
            batch_names = sorted(
                queue,
                key=lambda name: (-critical_scores.get(name, 0.0), name),
            )
            queue.clear()

            self._batches.append([self._tasks[n] for n in batch_names])
            scheduled += len(batch_names)

            for name in batch_names:
                for dep_name in dependents[name]:
                    in_degree[dep_name] -= 1
                    if in_degree[dep_name] == 0:
                        queue.append(dep_name)

        if scheduled != len(self._tasks):
            unscheduled = {
                name
                for name in self._tasks
                if name not in {t.name for batch in self._batches for t in batch}
            }
            raise CyclicDependencyError(
                f"Cyclic dependency detected among tasks: {unscheduled}"
            )

    def _schedule_subset(self, subset_names: set[str]) -> list[list[BuildTask]]:
        """Topologically schedule a subset of tasks."""
        deps: dict[str, set[str]] = {name: set() for name in subset_names}
        producers: dict[str, str] = {}
        for name in subset_names:
            for key in self._tasks[name].produces:
                producers[key] = name

        for name in subset_names:
            task = self._tasks[name]
            for req in task.requires:
                dep_name = producers.get(req)
                if dep_name is not None and dep_name != name:
                    deps[name].add(dep_name)

        in_degree: dict[str, int] = {name: len(dep_set) for name, dep_set in deps.items()}
        dependents: dict[str, list[str]] = defaultdict(list)
        for name, dep_set in deps.items():
            for dep in dep_set:
                dependents[dep].append(name)

        critical_scores = self._compute_critical_scores(dependents)

        queue: deque[str] = deque(name for name, degree in in_degree.items() if degree == 0)
        batches: list[list[BuildTask]] = []
        scheduled = 0

        while queue:
            batch_names = sorted(
                queue,
                key=lambda name: (-critical_scores.get(name, 0.0), name),
            )
            queue.clear()
            batches.append([self._tasks[name] for name in batch_names])
            scheduled += len(batch_names)
            for name in batch_names:
                for dependent in dependents[name]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        if scheduled != len(subset_names):
            unscheduled = {
                name
                for name in subset_names
                if name not in {t.name for batch in batches for t in batch}
            }
            raise CyclicDependencyError(
                f"Cyclic dependency detected in planned subset: {unscheduled}"
            )

        return batches

    def _compute_critical_scores(
        self,
        dependents: dict[str, list[str]],
    ) -> dict[str, float]:
        """Compute estimated critical-path scores for task prioritization."""
        memo: dict[str, float] = {}

        def score(name: str) -> float:
            cached = memo.get(name)
            if cached is not None:
                return cached

            own = self._task_durations_ms.get(name, 1.0)
            children = dependents.get(name, [])
            if not children:
                memo[name] = own
                return own

            child_max = max(score(child) for child in children)
            total = own + child_max
            memo[name] = total
            return total

        for task_name in self._tasks:
            score(task_name)
        return memo
