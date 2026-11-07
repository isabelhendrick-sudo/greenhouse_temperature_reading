#!/usr/bin/env python3
"""Plot greenhouse temperature and dew point by photo-session date.

Portable version of multi_figure_graph.ipynb. The attached figure is preserved
in figures/; this script writes regenerated figures and summaries to --out.
The time origin follows the original notebook: the latest sensor timestamp
for each photo date, not an independently verified photo timestamp.
"""
from __future__ import annotations

import argparse
import os
from contextlib import ExitStack
from pathlib import Path

import matplotlib
matplotlib.use("Agg")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path,
                        default=Path(os.environ.get("GREENHOUSE_DATA_DIR", "data/2.Validation")),
                        help="Validation folder containing the label and sensor subfolders (see README)")
    parser.add_argument("--out", type=Path, default=Path("outputs"),
                        help="Destination for regenerated figures and result tables")
    return parser.parse_args()


def run(args, archives):
    #libraries, folder paths and settings 
    import io
    import json
    import zipfile
    from pathlib import Path

    import pandas as pd
    import matplotlib.pyplot as plt


    # Where the data is, and where outputs are saved
    BASE = args.data_dir
    LABELS = BASE / "라벨링데이터"
    SENSORS = BASE / "환경센서"
    OUT = args.out
    OUT.mkdir(parents=True, exist_ok=True)

    # Names for the condition codes
    CODE_NAMES = {"00": "Healthy", "a1": "a1", "a2": "a2", "b1": "b1", "b6": "b6",
                  "b7": "b7", "b8": "b8", "c1": "c1", "c2": "c2"}

    # Air within 2 °C of its dew point counts as near condensation
    CONDENSATION_GAP = 2.0

    print("Labels folder found:", LABELS.exists())
    print("Sensor folder found:", SENSORS.exists())
    print("Figures will be saved in:", OUT)
    if not LABELS.is_dir() or not SENSORS.is_dir():
        raise ValueError("The data folder must contain the label and sensor subfolders listed in README.md.")

    # Prefer archived copies when archives and extracted duplicates coexist.
    # Deduplicate stems before reading; archive handles close when the run ends.
    def files_in(folder, ending):
        files = list(folder.rglob("*"))
        seen = set()
        for f in files:
            if f.is_file() and f.suffix.lower() == ".zip":
                z = archives.enter_context(zipfile.ZipFile(f))
                for info in z.infolist():
                    if not info.is_dir() and info.filename.lower().endswith(ending):
                        stem = Path(info.filename).stem
                        if stem not in seen:
                            seen.add(stem)
                            yield stem, (lambda z=z, i=info: z.read(i))
        for f in files:
            if f.is_file() and f.suffix.lower() == ending and f.stem not in seen:
                seen.add(f.stem)
                yield f.stem, f.read_bytes


    #load the labels 
    labels =[]
    for stem, read in files_in(LABELS, ".json"): 
        d = json.loads(read().decode("utf-8-sig"))
        desc, a = d["description"], d["annotations"]
        labels.append({"stem": stem, "date": pd.to_datetime(desc["date"]),
                       "hour":str(desc.get("time", ""))[:2], "code": a.get("disease"), "risk": a.get("risk")})

    # Duplicate stems can occur across ZIP archives and extracted copies.
    if not labels:
        raise ValueError("No JSON labels found.")
    labels = pd.DataFrame(labels).drop_duplicates("stem")
    print(len(labels), "labels")

    #find each photo's farm and pick Farm 01 
    sensors = dict(files_in(SENSORS, ".csv"))

    #read only the first row of each CSV to get farm name 
    farm_of = {}
    for stem in labels.stem: 
        if stem in sensors:
            first = pd.read_csv(io.BytesIO(sensors[stem]()), encoding="cp949", nrows=1)
            farm_of[stem] = first.filter(like="농지").iloc[0, 0]

    #replace real farm names with anonymous codes 
    codes = {name: f"Farm {i + 1:02d}" for i, name in enumerate(sorted(set(farm_of.values())))}
    labels["farm"] = labels.stem.map(farm_of).map(codes)

    if labels.farm.notna().sum() == 0:
        raise ValueError("No labels match sensor files by filename stem.")
    # Keep the farm photographed on the most dates 
    farm = labels.groupby("farm").date.nunique().idxmax()
    lab = labels[labels.farm == farm]
    print(farm, "=", len(lab), "photos on", lab.date.nunique(), "dates")

    #load the farm's sensor readings 
    def read_sensor(data):
        df = pd.read_csv(io.BytesIO(data), encoding="cp949")
        find = lambda word: next(c for c in df.columns if word in c)
        return pd.DataFrame({"time": pd.to_datetime(df[find("측정시각")]), "temp": df[find("온도")],
                             "rh": df[find("습도")], "co2": df[find("CO2")], "dew": df[find("이슬점")]})

    # One file per condition, photo date and photo hour; preserve original selection order.
    picks = lab.drop_duplicates(["code", "date", "hour"])
    frames = []
    for _, row in picks.iterrows():
        s = read_sensor(sensors[row.stem]())
        s["code"], s["photo_date"] = row.code, row.date
        frames.append(s)

    env_all = pd.concat(frames).drop_duplicates(["photo_date", "time"]).sort_values("time")
    env = env_all.drop_duplicates(["code", "time"]).copy()
    env["gap"] = env.temp - env.dew
    print(len(picks), "sensor files read,", len(env), "readings")


    #table of condition periods 
    from matplotlib.colors import to_rgb, to_hex

    PALETTE = ["#1b9e77", "#d95f02", "#7570b3", "#e7298a", "#66a61e", "#e6ab02", "#a6761d", "#666666"]
    MUTE = 0.35      # 0 = original colours, 1 = fully grey


    def mute(colour, amount=MUTE, grey="#8c8c8c"):
        """Blend a colour towards grey to make it less vibrant."""
        c, g = to_rgb(colour), to_rgb(grey)
        return to_hex([x * (1 - amount) + y * amount for x, y in zip(c, g)])


    per = lab.groupby("code").agg(first=("date", "min"), last=("date", "max"),
                                  photos=("stem", "size"), dates=("date", "nunique")).sort_values("first")
    per["name"] = [CODE_NAMES.get(c, c) for c in per.index]
    per["colour"] = [mute(PALETTE[i % len(PALETTE)]) for i in range(len(per))]
    per["label"] = [f"{n}\n{a.day} {a:%b} \u2013 {b.day} {b:%b}" if a != b else f"{n}\n{a.day} {a:%b %Y}"
                    for n, a, b in zip(per.name, per["first"], per["last"])]

    import math

    # Standard matplotlib look: boxed panels, ticks pointing inwards
    plt.rcdefaults()
    plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"],
                         "font.size": 9, "axes.linewidth": 0.8, "xtick.direction": "in",
                         "ytick.direction": "in", "savefig.dpi": 300})

    Y_MIN, Y_MAX = env_all.dew.min() - 1, env_all.temp.max() + 1
    dates = sorted(lab.date.unique())


    def plot_session(ax, date):
        w = env_all[env_all.photo_date == date].set_index("time").sort_index()
        code = lab.loc[lab.date == date, "code"].iloc[0]
        hours = (w.index - w.index.max()).total_seconds() / 3600
        ax.fill_between(hours, w.dew, w.temp, where=(w.temp - w.dew) < CONDENSATION_GAP,
                        color="#f4a582", lw=0)
        ax.plot(hours, w.temp, color=per.loc[code, "colour"], lw=1.2)
        ax.plot(hours, w.dew, color="0.4", lw=0.8, ls="--")
        ax.set_title(f"{date:%Y-%m-%d} ({CODE_NAMES.get(code, code)})", fontsize=9, fontweight="bold")
        ax.set_xlim(-48, 0)
        ax.set_xticks([-48, -36, -24, -12, 0])
        ax.set_ylim(Y_MIN, Y_MAX)
        ax.grid(color="0.9", lw=0.5)

    (OUT / "sessions").mkdir(exist_ok=True)

    for date in dates:
        date = pd.Timestamp(date)
        fig, ax = plt.subplots(figsize=(5, 3.5))
        plot_session(ax, date)
        ax.set_xlabel("Hours before photo")
        ax.set_ylabel("Temperature (\u00b0C)")
        fig.tight_layout()
        fig.savefig(OUT / "sessions" / f"session_{date:%Y%m%d}.png")
        plt.close(fig)

    print(len(dates), "figures saved in", (OUT / "sessions").resolve())

    cols = 5
    rows = math.ceil(len(dates) / cols)
    fig, axs = plt.subplots(rows, cols, figsize=(15, 2.6 * rows + 1), sharex=True, sharey=True)
    axs = axs.ravel()

    for ax, date in zip(axs, dates):
        plot_session(ax, pd.Timestamp(date))
    for k, ax in enumerate(axs):
        if k >= len(dates):
            ax.axis("off")
        elif k + cols >= len(dates):
            ax.tick_params(labelbottom=True)

    fig.suptitle(f"Greenhouse temperature 48 hr before each photo session | {farm}, 2021-2022",
                 fontsize=14, fontweight="bold")
    fig.supxlabel("Hours before photo", fontsize=11)
    fig.supylabel("Temperature (\u00b0C)", fontsize=11, x=0.005)

    handles = [plt.Line2D([], [], color=r.colour, lw=1.5, label=r["name"]) for _, r in per.iterrows()]
    handles += [plt.Line2D([], [], color="0.4", lw=0.8, ls="--", label="Dew point"),
                plt.Rectangle((0, 0), 1, 1, color="#f4a582",
                              label=f"Within {CONDENSATION_GAP:g} \u00b0C of dew point")]
    fig.legend(handles=handles, loc="center", bbox_to_anchor=(0.7, 0.13), ncol=2, fontsize=9, frameon=False)

    fig.tight_layout(rect=[0.015, 0, 1, 0.97])
    fig.savefig(OUT / "f4_photo_sessions.png")
    plt.close(fig)
    print("Saved:", (OUT / "f4_photo_sessions.png").resolve())

    # Summaries use only points in the visible [-48, 0] hour window.
    # Percentages are shares of valid readings, not estimates of exposure hours.
    rows = []
    for date in dates:
        date = pd.Timestamp(date)
        w = env_all[env_all.photo_date == date].sort_values("time")
        end = w.time.max()
        w = w[w.time >= end - pd.Timedelta(hours=48)].copy()
        valid = w[["temp", "dew"]].notna().all(axis=1)
        gap = w.loc[valid, "temp"] - w.loc[valid, "dew"]
        session = lab[lab.date == date]
        intervals = w.time.diff().dt.total_seconds().div(60).dropna()
        rows.append({
            "photo_date": date.strftime("%Y-%m-%d"),
            "panel_code": session.code.iloc[0],
            "all_codes_on_date": ";".join(sorted(session.code.unique())),
            "photos": len(session),
            "window_start": w.time.min(), "window_end": end,
            "sensor_end_matches_photo_date": end.normalize() == date.normalize(),
            "sensor_end_date_lag_days": (date.normalize() - end.normalize()).days,
            "sensor_readings": len(w), "valid_gap_readings": len(gap),
            "temperature_min_c": w.temp.min(), "temperature_max_c": w.temp.max(),
            "temperature_mean_c": w.temp.mean(),
            "dew_point_min_c": w.dew.min(), "dew_point_max_c": w.dew.max(),
            "near_dew_point_readings": int((gap < CONDENSATION_GAP).sum()),
            "near_dew_point_reading_pct": (gap < CONDENSATION_GAP).mean() * 100,
            "negative_gap_readings": int((gap < 0).sum()),
            "largest_sampling_interval_minutes": intervals.max(),
        })
    pd.DataFrame(rows).to_csv(OUT / "session_summary.csv", index=False, float_format="%.4f")
    for row in rows:
        if not row["sensor_end_matches_photo_date"]:
            print("WARNING: photo date", row["photo_date"], "has sensor endpoint", row["window_end"])
    per[["first", "last", "photos", "dates"]].to_csv(OUT / "condition_summary.csv")
    farm_summary = labels.groupby("farm").agg(
        photos=("stem", "size"), dates=("date", "nunique"),
        first=("date", "min"), last=("date", "max"))
    farm_summary.to_csv(OUT / "farm_summary.csv")
    print("Saved summaries in:", OUT.resolve())


def main():
    args = parse_args()
    with ExitStack() as archives:
        run(args, archives)


if __name__ == "__main__":
    main()
