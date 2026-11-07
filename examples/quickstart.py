"""Run after: python -m pip install -e .  Requires public API access."""
from apexium import Apexium

client = Apexium()
events = client.openf1.meetings(year=2025)
print(f"OpenF1 meetings: {len(events)}")
if events:
    print(events[0].get("meeting_name"))

standings = client.jolpica.driver_standings(2025)
if standings:
    print("First championship entry:", standings[0].get("season"))
