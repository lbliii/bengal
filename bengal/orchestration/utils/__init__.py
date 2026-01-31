"""
Shared utilities for orchestration modules.

This package provides common utilities extracted from orchestrators to reduce
code duplication and improve maintainability:

- parallel: Parallel processing with error aggregation and progress tracking
- i18n: Internationalization configuration helpers
- virtual_pages: Virtual/generated page creation utilities
- errors: Orchestration-specific error handling

Example:
    >>> from bengal.orchestration.utils import ParallelProcessor, get_site_languages
    >>> processor = ParallelProcessor(workload_type=WorkloadType.IO_BOUND)
    >>> languages = get_site_languages(site.config)

"""

from bengal.orchestration.utils.errors import (
    handle_orchestration_error,
    is_shutdown_error,
)
from bengal.orchestration.utils.i18n import (
    I18nConfig,
    get_i18n_config,
    get_site_languages,
    is_i18n_enabled,
)
from bengal.orchestration.utils.parallel import (
    BatchProgressUpdater,
    ParallelProcessor,
)
from bengal.orchestration.utils.virtual_pages import (
    VirtualPageSpec,
    claim_url_gracefully,
    create_virtual_page,
)

__all__ = [
    "BatchProgressUpdater",
    "I18nConfig",
    "ParallelProcessor",
    "VirtualPageSpec",
    "claim_url_gracefully",
    "create_virtual_page",
    "get_i18n_config",
    "get_site_languages",
    "handle_orchestration_error",
    "is_i18n_enabled",
    "is_shutdown_error",
]
