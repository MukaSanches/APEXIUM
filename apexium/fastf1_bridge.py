"""Optional FastF1 bridge; not downloaded or imported until explicitly requested."""


def load_session(year: int, grand_prix: str, session: str = "R",
                 *, telemetry: bool = True, weather: bool = True,
                 messages: bool = True):
    """Return a loaded FastF1 Session (optional dependency and its semantics apply)."""
    try:
        import fastf1
    except ImportError as exc:
        raise ImportError("Install with: pip install apexium-f1[fastf1]") from exc
    selected = fastf1.get_session(year, grand_prix, session)
    selected.load(telemetry=telemetry, weather=weather, messages=messages)
    return selected
