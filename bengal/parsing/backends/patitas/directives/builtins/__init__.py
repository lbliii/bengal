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

from bengal.parsing.backends.patitas.directives.builtins.admonition import (
    AdmonitionDirective,
)
from bengal.parsing.backends.patitas.directives.builtins.button import (
    ButtonDirective,
)
from bengal.parsing.backends.patitas.directives.builtins.cards import (
    CardDirective,
    CardsDirective,
    ChildCardsDirective,
)
from bengal.parsing.backends.patitas.directives.builtins.checklist import (
    ChecklistDirective,
)
from bengal.parsing.backends.patitas.directives.builtins.code_tabs import (
    CodeTabsDirective,
)
from bengal.parsing.backends.patitas.directives.builtins.container import (
    ContainerDirective,
)
from bengal.parsing.backends.patitas.directives.builtins.data_table import (
    DataTableDirective,
)
from bengal.parsing.backends.patitas.directives.builtins.dropdown import (
    DropdownDirective,
)
from bengal.parsing.backends.patitas.directives.builtins.embed import (
    CodePenDirective,
    CodeSandboxDirective,
    GistDirective,
    SoundCloudDirective,
    SpotifyDirective,
    StackBlitzDirective,
)
from bengal.parsing.backends.patitas.directives.builtins.include import (
    IncludeDirective,
    LiteralIncludeDirective,
)
from bengal.parsing.backends.patitas.directives.builtins.inline import (
    BadgeDirective,
    IconDirective,
    RubricDirective,
    TargetDirective,
)
from bengal.parsing.backends.patitas.directives.builtins.media import (
    AudioDirective,
    FigureDirective,
    GalleryDirective,
)
from bengal.parsing.backends.patitas.directives.builtins.misc import (
    AsciinemaDirective,
    BuildDirective,
    ExampleLabelDirective,
)
from bengal.parsing.backends.patitas.directives.builtins.navigation import (
    BreadcrumbsDirective,
    PrevNextDirective,
    RelatedDirective,
    SiblingsDirective,
)
from bengal.parsing.backends.patitas.directives.builtins.steps import (
    StepDirective,
    StepsDirective,
)
from bengal.parsing.backends.patitas.directives.builtins.tables import (
    ListTableDirective,
)
from bengal.parsing.backends.patitas.directives.builtins.tabs import (
    TabItemDirective,
    TabSetDirective,
)
from bengal.parsing.backends.patitas.directives.builtins.versioning import (
    ChangedDirective,
    DeprecatedDirective,
    SinceDirective,
)
from bengal.parsing.backends.patitas.directives.builtins.video import (
    SelfHostedVideoDirective,
    TikTokDirective,
    VimeoDirective,
    YouTubeDirective,
)

__all__ = [
    # Admonitions
    "AdmonitionDirective",
    # Miscellaneous
    "AsciinemaDirective",
    # Media
    "AudioDirective",
    # Inline
    "BadgeDirective",
    # Navigation
    "BreadcrumbsDirective",
    "BuildDirective",
    # Button
    "ButtonDirective",
    # Cards
    "CardDirective",
    "CardsDirective",
    # Versioning
    "ChangedDirective",
    # Checklist
    "ChecklistDirective",
    "ChildCardsDirective",
    # Embed
    "CodePenDirective",
    "CodeSandboxDirective",
    # Code Tabs
    "CodeTabsDirective",
    # Container
    "ContainerDirective",
    # Data Table
    "DataTableDirective",
    "DeprecatedDirective",
    # Dropdown
    "DropdownDirective",
    "ExampleLabelDirective",
    "FigureDirective",
    "GalleryDirective",
    "GistDirective",
    "IconDirective",
    # Include (File I/O)
    "IncludeDirective",
    # Tables
    "ListTableDirective",
    "LiteralIncludeDirective",
    "PrevNextDirective",
    "RelatedDirective",
    "RubricDirective",
    # Video
    "SelfHostedVideoDirective",
    "SiblingsDirective",
    "SinceDirective",
    "SoundCloudDirective",
    "SpotifyDirective",
    "StackBlitzDirective",
    # Steps
    "StepDirective",
    "StepsDirective",
    # Tabs
    "TabItemDirective",
    "TabSetDirective",
    "TargetDirective",
    "TikTokDirective",
    "VimeoDirective",
    "YouTubeDirective",
]
