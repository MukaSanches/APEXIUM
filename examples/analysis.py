"""Historical 2025 Brazil — descriptive metrics using available OpenF1 data."""
from apexium import Apexium

race = Apexium().race(2025, "Brazil")
print("Meeting:", race.meeting.get("meeting_name"))
print("Drivers:", len(race.drivers()))
print("Top observed median race laps:", race.pace_analysis()[:5])
print("Reported pit entries:", race.pit_analysis()[:5])
print("Lap data quality:", race.data_quality())
