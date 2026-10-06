"""Which facts may be written to long-term memory. The store does not decide this."""

_ALLOWED = frozenset({"committee_outcome", "watchlist_status"})


def may_remember(kind: str) -> bool:
    return kind in _ALLOWED
