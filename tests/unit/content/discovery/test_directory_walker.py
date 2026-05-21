from __future__ import annotations

from types import SimpleNamespace

from bengal.content.discovery.directory_walker import DirectoryWalker


def test_versioning_infrastructure_is_discovered_in_folder_mode(tmp_path) -> None:
    walker = DirectoryWalker(
        tmp_path,
        site=SimpleNamespace(
            versioning_enabled=True,
            version_config=SimpleNamespace(is_git_mode=False),
        ),
    )
    versions_dir = tmp_path / "_versions"

    assert walker.should_skip_item(versions_dir) is False
    assert walker.is_versioning_infrastructure(versions_dir) is True


def test_versioning_infrastructure_is_skipped_in_git_mode(tmp_path) -> None:
    walker = DirectoryWalker(
        tmp_path,
        site=SimpleNamespace(
            versioning_enabled=True,
            version_config=SimpleNamespace(is_git_mode=True),
        ),
    )
    versions_dir = tmp_path / "_versions"

    assert walker.should_skip_item(versions_dir) is True
    assert walker.is_versioning_infrastructure(versions_dir) is False
