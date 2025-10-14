"""
Stateful integration tests for build workflows using Hypothesis.

These tests simulate real user workflows with multiple steps,
automatically generating hundreds of different sequences.
"""

import string

from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, invariant, precondition, rule

from .helpers import (
    cache_exists,
    clean_site,
    create_temp_site,
    delete_page,
    hash_outputs,
    run_build,
    write_page,
)


# Strategies for generating test data
def page_names():
    """Generate valid page names."""
    return st.text(
        alphabet=string.ascii_lowercase + string.digits + "-", min_size=3, max_size=20
    ).map(lambda s: f"page-{s}.md")  # Prefix with 'page-' to avoid reserved names


def page_titles():
    """Generate page titles."""
    return st.text(min_size=5, max_size=50)


class PageLifecycleWorkflow(RuleBasedStateMachine):
    """
    Simulates realistic page management workflows.

    Hypothesis will generate sequences like:
    - create foo → build → create bar → build → delete foo → build
    - create 3 pages → build → modify all → incremental → delete 1 → build

    This test verifies that Bengal maintains consistency across
    all possible sequences of create/modify/delete/build operations.
    """

    def __init__(self):
        super().__init__()
        self.site_dir = None
        self.pages = {}  # name -> {"exists": bool, "title": str}
        self.last_build_output = None
        self.build_count = 0
        # Only run invariants immediately after a build rule executes
        self.last_action_was_build = False

    @initialize()
    def setup_site(self):
        """Initialize a temporary test site."""
        self.site_dir = create_temp_site("lifecycle")
        self.pages = {}
        self.last_build_output = None
        self.build_count = 0
        self.last_action_was_build = False

    @rule(name=page_names(), title=page_titles())
    def create_page(self, name, title):
        """
        Create a new page.

        This simulates a user creating content with `bengal new page` or
        manually creating a markdown file.
        """
        # Store page metadata
        self.pages[name] = {
            "exists": True,
            "title": title,
            "modified_count": 0,
        }

        # Write the actual file
        write_page(self.site_dir, name, title, content=f"Content for {title}")
        # Not a build action
        self.last_action_was_build = False

    @rule()
    @precondition(lambda self: any(v["exists"] for v in self.pages.values()))
    def modify_random_page(self):
        """
        Modify a random existing page.

        This simulates a user editing content.
        """
        # Get list of existing pages
        existing = [k for k, v in self.pages.items() if v["exists"]]
        if not existing:
            return

        # Pick the first one (Hypothesis will vary the state)
        name = existing[0]

        self.pages[name]["modified_count"] += 1

        new_title = f"{self.pages[name]['title']} (v{self.pages[name]['modified_count']})"
        self.pages[name]["title"] = new_title

        # Update the file
        write_page(
            self.site_dir,
            name,
            new_title,
            content=f"Updated content version {self.pages[name]['modified_count']}",
        )
        # Not a build action
        self.last_action_was_build = False

    @rule()
    @precondition(lambda self: any(v["exists"] for v in self.pages.values()))
    def delete_random_page(self):
        """
        Delete a random existing page.

        This simulates a user removing content.
        """
        # Get list of existing pages
        existing = [k for k, v in self.pages.items() if v["exists"]]
        if not existing:
            return

        # Pick the first one (Hypothesis will vary the state)
        name = existing[0]

        self.pages[name]["exists"] = False
        delete_page(self.site_dir, name)
        # Not a build action
        self.last_action_was_build = False

    @rule()
    @precondition(lambda self: len(self.pages) > 0)
    def full_build(self):
        """
        Run a full build.

        This simulates `bengal build`.
        """
        result = run_build(self.site_dir, incremental=False)
        self.last_build_output = result
        self.build_count += 1
        self.last_action_was_build = True

        # Important: After build, verify cleanup happened
        # This ensures deleted pages don't have output
        for name, meta in self.pages.items():
            if not meta["exists"]:
                expected_stem = name.replace(".md", "")
                expected_output = f"{expected_stem}/index.html"
                actual_path = self.site_dir / "public" / expected_output

                assert not actual_path.exists(), (
                    f"BUG: Deleted page '{name}' still has output after full_build! "
                    f"Path: {actual_path}"
                )

    @rule()
    @precondition(lambda self: len(self.pages) > 0 and self.build_count > 0)
    def incremental_build(self):
        """
        Run an incremental build.

        This simulates `bengal build` after initial build.
        """
        result = run_build(self.site_dir, incremental=True)
        self.last_build_output = result
        self.build_count += 1
        self.last_action_was_build = True

        # Important: After build, verify cleanup happened
        for name, meta in self.pages.items():
            if not meta["exists"]:
                expected_stem = name.replace(".md", "")
                expected_output = f"{expected_stem}/index.html"
                actual_path = self.site_dir / "public" / expected_output

                assert not actual_path.exists(), (
                    f"BUG: Deleted page '{name}' still has output after incremental_build! "
                    f"Path: {actual_path}"
                )

    @invariant()
    def build_succeeds(self):
        """Property: Builds should always succeed."""
        if not self.last_action_was_build:
            return
        if self.last_build_output:
            assert self.last_build_output[
                "success"
            ], f"Build failed with errors: {self.last_build_output['errors']}"

    @invariant()
    def active_pages_have_output(self):
        """
        Property: Active pages must have output files after build.

        If a page exists in content/, it must have corresponding HTML in public/.
        """
        if not self.last_action_was_build:
            return
        # Only check if we've done at least one build
        if self.build_count == 0:
            return

        if not self.last_build_output or not self.last_build_output["success"]:
            return  # Skip if no successful build yet

        # Only check if we have pages
        if not self.pages:
            return

        output_files = self.last_build_output["output_files"]

        for name, meta in self.pages.items():
            if meta["exists"]:
                # Expect output like "page-name/index.html" (pretty URLs)
                expected_stem = name.replace(".md", "")
                expected_output = f"{expected_stem}/index.html"

                # Check if the file exists on disk, not just in our tracked list
                actual_path = self.site_dir / "public" / expected_output

                assert actual_path.exists(), (
                    f"Active page '{name}' should have output file '{expected_output}' at {actual_path}, "
                    f"but it doesn't exist. Files in output: {sorted([str(f) for f in output_files])[:10]}"
                )

    @invariant()
    def deleted_pages_have_no_output(self):
        """
        Property: Deleted pages must not have output files.

        If a page was deleted from content/, its HTML should not appear in public/.
        """
        if not self.last_action_was_build:
            return
        # Only check if we've done at least one build
        if self.build_count == 0:
            return

        if not self.last_build_output or not self.last_build_output["success"]:
            return  # Skip if no successful build yet

        # Only check if we have any deleted pages
        deleted_pages = [name for name, meta in self.pages.items() if not meta["exists"]]
        if not deleted_pages:
            return

        for name in deleted_pages:
            # Deleted pages should not have output
            expected_stem = name.replace(".md", "")
            expected_output = f"{expected_stem}/index.html"
            actual_path = self.site_dir / "public" / expected_output

            assert not actual_path.exists(), (
                f"Deleted page '{name}' should NOT have output file, "
                f"but '{actual_path}' still exists"
            )

    @invariant()
    def cache_created_after_build(self):
        """
        Property: Build should create a cache file.

        After a successful build, .bengal/cache.json should exist.
        """
        if not self.last_action_was_build:
            return
        if self.build_count > 0 and self.last_build_output and self.last_build_output["success"]:
            assert cache_exists(self.site_dir), "Build cache should exist after successful build"

    def teardown(self):
        """Clean up temporary site."""
        if self.site_dir:
            clean_site(self.site_dir)


# Convert to pytest test case
TestPageLifecycleWorkflow = PageLifecycleWorkflow.TestCase


class IncrementalConsistencyWorkflow(RuleBasedStateMachine):
    """
    Critical test: Incremental builds must produce identical output to full builds.

    This is THE most important property for an SSG. Users expect:
    - `bengal build` (full)
    - modify one file
    - `bengal build` (incremental)
    - → result should be identical to full rebuild

    Hypothesis will generate many sequences to test this property.
    """

    def __init__(self):
        super().__init__()
        self.site_dir = None
        self.pages = {}
        self.full_build_hashes = None
        self.incremental_build_hashes = None

    @initialize()
    def setup_site(self):
        """Initialize test site with some initial pages."""
        self.site_dir = create_temp_site("consistency")

        # Create 3 initial pages to make it interesting
        for i in range(3):
            name = f"page-{i}.md"
            title = f"Page {i}"
            self.pages[name] = {"title": title}
            write_page(self.site_dir, name, title)

        # Do initial build
        run_build(self.site_dir, incremental=False)

    @rule()
    @precondition(lambda self: len(self.pages) > 0)
    def modify_random_page(self):
        """Modify a random page."""
        if not self.pages:
            return

        # Pick first page (Hypothesis will vary state)
        name = list(self.pages.keys())[0]
        new_title = f"{self.pages[name]['title']} (modified)"
        self.pages[name]["title"] = new_title
        write_page(self.site_dir, name, new_title)

    @rule()
    def full_build_and_snapshot(self):
        """Run full build and save output hashes."""
        run_build(self.site_dir, incremental=False)
        self.full_build_hashes = hash_outputs(self.site_dir)

    @rule()
    def incremental_build_and_snapshot(self):
        """Run incremental build and save output hashes."""
        run_build(self.site_dir, incremental=True)
        self.incremental_build_hashes = hash_outputs(self.site_dir)

    @invariant()
    def incremental_matches_full(self):
        """
        Property: Incremental build output must match full build output.

        This is the core contract of incremental builds.
        """
        if self.full_build_hashes and self.incremental_build_hashes:
            # Compare file sets
            full_files = set(self.full_build_hashes.keys())
            inc_files = set(self.incremental_build_hashes.keys())

            assert full_files == inc_files, (
                f"Incremental build produced different files than full build.\n"
                f"Full only: {full_files - inc_files}\n"
                f"Incremental only: {inc_files - full_files}"
            )

            # Compare file contents, skipping llm-full.txt due to dynamic timestamp
            for file_path in full_files:
                if file_path == 'llm-full.txt':
                    continue
                full_hash = self.full_build_hashes[file_path]
                inc_hash = self.incremental_build_hashes[file_path]

                assert full_hash == inc_hash, (
                    f"File '{file_path}' has different content in incremental vs full build.\n"
                    f"Full hash: {full_hash}\n"
                    f"Incremental hash: {inc_hash}"
                )

    def teardown(self):
        """Clean up."""
        if self.site_dir:
            clean_site(self.site_dir)


TestIncrementalConsistencyWorkflow = IncrementalConsistencyWorkflow.TestCase


# Example output documentation
"""
EXAMPLE HYPOTHESIS WORKFLOW GENERATION
---------------------------------------

Hypothesis will automatically generate sequences like:

1. create page-1 → build → modify page-1 → build → delete page-1 → build
2. create page-a → create page-b → build → delete page-a → incremental
3. create page-x → build → modify page-x → incremental → full → compare
4. create 5 pages → build → delete 2 → modify 1 → incremental

Each sequence tests a different workflow path through the system.
If any sequence violates an invariant, Hypothesis will:
1. Report the exact sequence that failed
2. Attempt to shrink it to the minimal failing example
3. Provide a seed to reproduce the failure

To run these tests:
    pytest tests/integration/stateful/test_build_workflows.py -v

To see statistics:
    pytest tests/integration/stateful/test_build_workflows.py --hypothesis-show-statistics

To increase thoroughness (slower):
    pytest tests/integration/stateful/test_build_workflows.py --hypothesis-seed=random

These tests are MUCH more powerful than writing individual integration tests
because Hypothesis explores the entire state space automatically.
"""
