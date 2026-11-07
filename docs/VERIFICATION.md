# Verification record

Checked on 7 November 2026 using Python 3.13.9, pandas 2.3.3, NumPy 2.3.5 and Matplotlib 3.10.6.

- Ran the portable script end to end on the available source validation dataset.
- Reproduced 13,433 unique labels, 7,891 selected-farm photos, 17 photo dates and 66 selected sensor files.
- Generated the combined figure, 17 separate session figures and three CSV summaries.
- Compared every selected sensor file with its extracted counterpart: all 66 were byte-identical.
- Compared the script's session statistics with a separate calculation from the notebook's selected sensor histories: all 17 rows agree within CSV rounding.
- Verified the original supplied figure was copied byte-for-byte. Regenerated combined figure has identical pixels: **true**.
- Checked the notebook structure, Python syntax and all local Markdown links.
- Confirmed two sensor-end/photo-date mismatches (16 and 17 October 2021), both flagged in the CSV and described in the README.

The 4,909 rows counted across visible panels are repeated panel observations, not 4,909 independent sensor measurements. Overlapping windows reuse timestamps.

Raw data files, personal filesystem paths and farm names are not bundled. No new execution is claimed for the notebook's stored outputs; the standalone script was executed for verification.
