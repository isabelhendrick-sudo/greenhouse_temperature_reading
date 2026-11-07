# Methods and interpretation

## What is being compared?

This is a descriptive view of environmental histories associated with photo-session dates. It is not a disease prediction model, a treatment comparison, or a controlled experiment. A photo date can include several condition codes and many photographs from the same farm.

The original notebook identifies farms by sorting the distinct farm names in the matched sensor files and assigning `Farm 01`, `Farm 02`, and so on. These aliases are relative to the supplied dataset; adding or removing farms can change them. It selects the farm with the greatest number of distinct photo dates. In this dataset, that is Farm 01.

## Input and selection

1. Read JSON labels and CP949-encoded sensor CSVs, including ZIP members.
2. Match labels and CSVs using their filename stems. Keep one label per stem.
3. Extract the photo date, the first two characters of the photo time (the hour), and the condition code.
4. For the selected farm, choose the first label for each `(code, date, hour)` combination. This selects 66 sensor files in the supplied analysis.
5. Combine those sensor histories, keeping the first record for each `(photo_date, sensor_time)` pair. This prevents repeated copies at a timestamp from being plotted multiple times; conflicting values at the same timestamp are not averaged or reconciled.
6. Plot one panel for each of the 17 photo dates. The panel's colour and title use the first condition code encountered on that date.

The portable Python script prefers archived copies when the same stem exists in a ZIP and an extracted folder. It skips duplicate stems before reading and closes archive handles when finished. The notebook retains its original reader and first/last-copy behaviour. Use matching archive and extracted copies; remove or separate conflicting versions before analysis. The script preserves the original plotting and session-selection rules.

## The 48-hour axis

For each date, the original calculation is:

```python
hours = (sensor_time - latest_sensor_time_for_this_photo_date).total_seconds() / 3600
```

The axis displays `-48` through `0`. Thus, zero is the **latest selected sensor timestamp for that date**. The phrase “hours before photo” in the supplied figure assumes that this endpoint represents the photo session. The code does not independently align every photograph to its full timestamp. The included summary table records `window_start` and `window_end`, making the actual endpoints inspectable.

Input CSVs can contain readings outside the visible window. The exported numerical results use only timestamps in the final 48 hours, including both endpoints. They are not calculated from all rows of the selected files.

### Confirmed date mismatches

Two panels fail a basic check that the sensor endpoint falls on the photo date:

| Photo date / panel | Latest selected sensor timestamp | Date difference |
| --- | --- | --- |
| 2021-10-16 (b8) | 2021-10-06 09:20 | 10 days |
| 2021-10-17 (b8) | 2021-10-07 09:00 | 10 days |

These endpoints were checked against the source CSVs. The supplied notebook's stored `env.head()` output also shows early-October sensor readings associated with the 16 October photo date. The mismatch is not caused by relabelling the figure for this repository. The original figure is preserved, but these two panels must not be interpreted as verified conditions in the 48 hours before their labelled photo dates. They are retained in the CSV for auditability and marked `sensor_end_matches_photo_date=False`. The script prints a warning for them. Correct alignment requires resolving the source association; no arbitrary ten-day shift is applied.

The other 15 panel endpoints fall on their labelled dates. This date-level check does not establish exact alignment to every photograph. All visible windows have 10-minute spacing; 13 contain 289 readings over 48 hours and four contain 288 readings over 47 hours 50 minutes. No negative temperature-minus-dew-point gaps occur in these windows.

## Dew-point gap and shading

```python
gap_c = air_temperature_c - dew_point_c
near_dew_point = gap_c < 2.0
```

The supplied figure calls this “Within 2 °C of dew point”; the actual comparison is strictly **less than 2 °C**, not less than or equal to 2 °C. The shaded band fills the gap between the two lines where that rule is true. The area of shading is not a quantitative exposure measure.

The summary reports:

```text
near_dew_point_reading_pct =
    100 × number of valid readings with gap < 2 °C / number of valid gap readings
```

Valid gap readings have both temperature and dew point present. This is a **percentage of sampled readings**, not a percentage of the 48-hour duration. Missing intervals are not interpolated for the summary. `negative_gap_readings` separately flags values where dew point exceeds air temperature; the original shading condition would include them.

A small air-temperature/dew-point gap indicates air close to saturation. It does not prove that a leaf was wet. Surface condensation depends on the surface temperature relative to the dew point; leaf temperature and leaf-wetness observations are absent from this analysis. See [UMass Extension's explanation of greenhouse humidity and condensation](https://www.umass.edu/agriculture-food-environment/greenhouse-floriculture/fact-sheets/reducing-humidity-in-greenhouse).

## Limits on interpretation

- **Repeated windows:** adjacent dates reuse overlapping environmental histories. Peaks repeated in two panels may be the same event. Do not sum their readings or exposure estimates as independent observations.
- **Mixed condition labels:** 6, 7, 8, and 12 October contain b6, b7, and b8 labels. Their panels display b6 because it is the first code encountered, not because all photos have b6. The legend includes b7 even though no panel uses it as its title code.
- **Season and growth stage:** condition codes occur in different calendar periods. All a1 photos in Farm 01 have growth code 13; the other selected conditions have growth code 12. Temperature differences cannot be attributed to condition alone.
- **Farm separation:** all selected non-healthy condition labels belong to Farm 01, whereas healthy code 00 occurs in the other three farms. This dataset does not supply a healthy control group within Farm 01.
- **Selection and measurement:** one source file per condition/date/hour is a representative selection, not an independent environmental measurement for every photograph. Abrupt changes should be checked against sensor quality, humidity, and operating records before assigning a mechanism.
- **Scope:** the 17 sampled dates span October 2021 to January 2022; they do not form a continuous seasonal monitoring series. No statistical significance, causal effect, disease forecast, or crop-specific safe temperature threshold is established here.

## Reproduction

The dependency file records the versions available in the checked local Python 3.13.9 environment. `figures/f4_photo_sessions.png` is the supplied image, copied without alteration. The command-line script writes a regenerated figure, 17 individual panels, and CSV summaries to its output directory. Font availability can affect rendered appearance on another computer.

The notebook's stored results come from the supplied notebook. Its local paths were replaced for portability; it was not presented as a newly executed notebook. The original input files are preserved outside this repository.
