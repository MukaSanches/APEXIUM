# 20 descriptive analyses

Every function uses source data without inventing an unobserved measurement.

~~~python
from apexium import Apexium, analytics

race = Apexium().race(2025, "Brazil")
laps = race.laps()
stints = race.stints()
print(analytics.fastest_laps(laps)[:5])
print(analytics.ideal_laps(laps)[:5])
print(analytics.compound_pace(laps, stints)[:5])
print(analytics.lap_trends(laps)[:5])
~~~

## Core functions (6)

1. race_pace: descriptive per-driver medians, means, standard deviations and best laps.
2. pit_summary: pit entry counts, total lane time and stationary time only where observed.
3. position_changes: first-to-last sampled driver positions.
4. stint_summary: measured stint lengths and tyre age at the start.
5. overtaking_counts: provider-reported position swaps (includes pits/penalties).
6. lap_quality: duplicate keys, missing and invalid lap durations.

## Advanced functions (14)

7. fastest_laps: fastest valid recorded lap per driver, excluding pit-out laps.
8. ideal_laps: sum of three independently best sector times; **theoretical**, not a completed lap.
9. sector_pace: per-driver medians per sector, using all available measured sectors.
10. lap_trends: least-squares seconds-per-lap slope without tyre, fuel or weather controls.
11. compound_pace: median lap time by mapped observed compound/stint, excluding pit-out laps.
12. stint_strategies: ordered compound sequence and observed stint lengths.
13. pit_window_histogram: counts of pit entries by recorded lap number.
14. speed_summary: min, sample mean and max measured speed by driver.
15. throttle_brake_summary: share of telemetry samples with 95%+ throttle / nonzero brake.
16. drs_code_summary: frequency of DRS codes 10/12/14 in sampled car data; code meaning can vary.
17. weather_summary: arithmetic means of measured weather values, not duration weighted.
18. race_control_summary: counts of upstream messages by category and flag.
19. lap_deltas: per-lap time difference between two drivers on matching lap numbers.
20. position_trajectory: change-point list of a driver's observed position without interpolation.

## Important limits

- Comparisons do not automatically control for team performance, tyres, fuel, traffic, pit in/out laps, track evolution, safety cars, or weather.
- The datasets may contain missing values and delayed corrections.
- Samples from high-frequency telemetry are not necessarily uniformly spaced in distance or time.
- Never interpret sampled pedal percentages as distance or time exposure without resampling.
- No prediction accuracy or external performance guarantee is claimed.

When presenting analyses publicly, include the source URL, accessed date and methodology.
