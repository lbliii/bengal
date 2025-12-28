"""Built-in directive handlers.

Provides commonly-used directives out of the box:
    - Admonitions: note, warning, tip, danger, error, info, example, success, caution, seealso
    - Dropdown: collapsible content with icons, badges, colors
    - Tabs: tab-set and tab-item with sync and CSS state machine modes
    - Container: generic wrapper div with custom classes
    - Steps: numbered step-by-step guides with contracts
    - Cards: grid layout with card, cards, and child-cards directives
    - Checklist: styled lists with progress tracking
    - Media: figure, audio, and gallery directives
    - Tables: list-table directive for MyST-style tables
    - Video: youtube, vimeo, tiktok, and self-hosted video embeds
    - Embed: gist, codepen, codesandbox, stackblitz, spotify, soundcloud
    - Versioning: since, deprecated, changed version badges
"""

from __future__ import annotations

from bengal.rendering.parsers.patitas.directives.builtins.admonition import (
    AdmonitionDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.button import (
    ButtonDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.cards import (
    CardDirective,
    CardsDirective,
    ChildCardsDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.checklist import (
    ChecklistDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.code_tabs import (
    CodeTabsDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.container import (
    ContainerDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.data_table import (
    DataTableDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.dropdown import (
    DropdownDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.embed import (
    CodePenDirective,
    CodeSandboxDirective,
    GistDirective,
    SoundCloudDirective,
    SpotifyDirective,
    StackBlitzDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.include import (
    IncludeDirective,
    LiteralIncludeDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.inline import (
    BadgeDirective,
    IconDirective,
    RubricDirective,
    TargetDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.media import (
    AudioDirective,
    FigureDirective,
    GalleryDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.misc import (
    AsciinemaDirective,
    BuildDirective,
    ExampleLabelDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.navigation import (
    BreadcrumbsDirective,
    PrevNextDirective,
    RelatedDirective,
    SiblingsDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.steps import (
    StepDirective,
    StepsDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.tables import (
    ListTableDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.tabs import (
    TabItemDirective,
    TabSetDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.versioning import (
    ChangedDirective,
    DeprecatedDirective,
    SinceDirective,
)
from bengal.rendering.parsers.patitas.directives.builtins.video import (
    SelfHostedVideoDirective,
    TikTokDirective,
    VimeoDirective,
    YouTubeDirective,
)

__all__ = [
    # Admonitions
    "AdmonitionDirective",
    # Button
    "ButtonDirective",
    # Cards
    "CardDirective",
    "CardsDirective",
    "ChildCardsDirective",
    # Checklist
    "ChecklistDirective",
    # Code Tabs
    "CodeTabsDirective",
    # Container
    "ContainerDirective",
    # Data Table
    "DataTableDirective",
    # Dropdown
    "DropdownDirective",
    # Embed
    "CodePenDirective",
    "CodeSandboxDirective",
    "GistDirective",
    "SoundCloudDirective",
    "SpotifyDirective",
    "StackBlitzDirective",
    # Include (File I/O)
    "IncludeDirective",
    "LiteralIncludeDirective",
    # Inline
    "BadgeDirective",
    "IconDirective",
    "RubricDirective",
    "TargetDirective",
    # Media
    "AudioDirective",
    "FigureDirective",
    "GalleryDirective",
    # Miscellaneous
    "AsciinemaDirective",
    "BuildDirective",
    "ExampleLabelDirective",
    # Navigation
    "BreadcrumbsDirective",
    "PrevNextDirective",
    "RelatedDirective",
    "SiblingsDirective",
    # Steps
    "StepDirective",
    "StepsDirective",
    # Tables
    "ListTableDirective",
    # Tabs
    "TabItemDirective",
    "TabSetDirective",
    # Versioning
    "ChangedDirective",
    "DeprecatedDirective",
    "SinceDirective",
    # Video
    "SelfHostedVideoDirective",
    "TikTokDirective",
    "VimeoDirective",
    "YouTubeDirective",
]
