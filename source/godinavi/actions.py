from dataclasses import dataclass
from typing import Callable


Action = Callable[[], None]


@dataclass(frozen=True)
class QuickAction:
    label: str | Callable[[], str]
    callback: Action
    enabled: Callable[[], bool] | None = None


@dataclass(frozen=True)
class DockItem:
    key: str
    symbol: str
    label: str
    primary: Action
    quick_actions: tuple[QuickAction, ...] = ()
    icon_path: str | None = None
    show_flyout: bool = True
    state: Callable[[], bool] | None = None
    secondary: Action | None = None
    badge: Callable[[], str] | None = None
    alert: Callable[[], str] | None = None
    icon_text: str | None = None
    icon_bottom_text: str | None = None
