from pathlib import Path    # Path helps Python work with folders and file
import numpy as np
import pandas as pd

SEED = 42          #reproducibility
N = 2000           # number of projects
DELAY_THRESHOLD = 0.20   # delayed if eventual delay > 20% of planned duration

rng = np.random.default_rng(SEED)   # the one random generator used everywhere


# sector -> (share of portfolio, typical planned duration in months,
#            probability land acquisition is needed, extra delay risk)
SECTORS = {
    "Roads & Highways":  (0.35, 30, 0.85,  0.03),
    "Railways":          (0.15, 48, 0.80,  0.06),
    "Water":             (0.15, 30, 0.50,  0.00),
    "Energy":            (0.12, 36, 0.45,  0.02),
    "Healthcare":        (0.08, 24, 0.30, -0.02),
    "Urban Development": (0.15, 36, 0.60,  0.04),
}

STATES = ["Maharashtra", "Gujarat", "Karnataka", "Rajasthan", "Tamil Nadu", "Uttar Pradesh",
          "Madhya Pradesh", "Odisha", "Telangana", "West Bengal", "Delhi", "Kerala"]

STATE_Possibilies = np.array([14, 10, 9, 9, 9, 13, 8, 6, 6, 6, 4, 6], dtype=float)   # State probabilities cause some states will appear more frequently than others.
STATE_Possibilies /= STATE_Possibilies.sum()   # probabilities must add up to 1




sector = rng.choice(list(SECTORS), size=N, p=[v[0] for v in SECTORS.values()])   # Pick a sector for each of the 2,000 projects. p stands for the probabilities  so here "Roads & Highways" will occurs more that "Medicalhealth"
state = rng.choice(STATES, size=N, p=STATE_Possibilies)   # Randomly choose a state according to our defined probabilities.






# Cost: log-normal => many small/medium projects, few very large ones (right-skewed)

cost = np.exp(rng.normal(loc=6.0, scale=1.0, size=N))        # median about 400 crore
cost = np.clip(cost, 50, 20000)    # Minimun costs value of project should be 50cr and Maximum should be 20000cr



# Planned duration: sector's typical duration, a little longer for bigger projects, plus noise
base_dur = np.array([SECTORS[s][1] for s in sector], dtype=float)
duration = base_dur * (cost / 400) ** 0.15 * np.exp(rng.normal(0, 0.25, N))
duration = np.clip(np.round(duration), 12, 96).astype(int)



# Contractor experience: roughly bell-shaped around 12 years, never below 1 or above 30
experience = np.clip(np.round(rng.normal(12, 6, N)), 1, 30).astype(int)

# Land acquisition needed? depends on sector
land_required = (rng.random(N) < np.array([SECTORS[s][2] for s in sector])).astype(int)


# 2. Snapshot: "Given what we know about the project right now, is this project at risk?" (D-009: always before the deadline)

frac = rng.uniform(0.10, 0.95, N)                       # share of planned time elapsed
months_elapsed = np.clip(np.round(frac * duration), 1, duration).astype(int)
frac = months_elapsed / duration                        # recompute after rounding (exact value)

# ----------------------------------------------------------------------------
# 3. Observed progress variables (these are the model's inputs)
# ----------------------------------------------------------------------------
# Quality of execution: experienced contractors do a bit better, plus lots of randomness
quality = 0.04 * (experience - 12) + rng.normal(0, 0.9, N)

# Physical progress ~ elapsed time x a "speed" factor. Speed < 1 means behind schedule.
speed = np.exp(0.12 * quality + rng.normal(0, 0.16, N))
progress = np.clip(100 * frac * speed, 1, 100)

# Spending usually runs a little AHEAD of physical progress (advances, mobilisation)
expenditure = np.clip(progress * np.exp(rng.normal(0.10, 0.18, N)) + rng.uniform(0, 6, N), 1, 100)

# Land acquired: improves with time. Beta distribution keeps values in 0..100 with spread.
mean_land = np.clip(0.30 + 0.65 * frac, 0.05, 0.97)
k = 6.0                                                 # concentration: higher = less spread
land_pct = 100 * rng.beta(mean_land * k, (1 - mean_land) * k)
land_pct = np.where(rng.random(N) < 0.12, 100.0, land_pct)   # some projects are fully acquired
land_pct = np.where(land_required == 1, land_pct, 100.0)     # D-007: not required -> 100

# ----------------------------------------------------------------------------
# 4. HIDDEN eventual outcome (D-008). The model never sees this column.
# ----------------------------------------------------------------------------
prog_frac = np.clip(progress / 100, 0.03, 1.0)
# If the current pace continued, total time would be frac/prog_frac times the plan.
pace_ratio = frac / prog_frac
# Early on we trust the plan more (shrink toward 1); later the observed pace matters more.
ratio = frac * pace_ratio + (1 - frac) * 1.0
# Future uncertainty is bigger early in the project than late.
sigma = 0.05 + 0.25 * (1 - frac)
ratio = ratio * np.exp(rng.normal(0, sigma))

land_gap = (100 - land_pct) / 100
# Spending far ahead of physical progress signals cost pressure / stalled work.
# Only the part beyond a normal 10-point lead counts.
spend_pressure = np.maximum(expenditure - progress - 10, 0) / 100
sector_risk = np.array([SECTORS[s][3] for s in sector])
size_risk = 0.03 * (np.log(cost) - 6.0)
experience_effect = -0.006 * (experience - 12)

# Unobserved future events (legal dispute, force majeure ...): rare but can be large
shock = np.where(rng.random(N) < 0.10, rng.exponential(0.25, N), 0.0)

eventual_delay_frac = (ratio - 1.0) + 0.25 * land_gap + 0.5 * spend_pressure + sector_risk + size_risk + experience_effect + shock
eventual_delay_frac = np.maximum(eventual_delay_frac, 0.0)     # no negative delay in this simulator

# ----------------------------------------------------------------------------
# 5. Assemble the datasets
# ----------------------------------------------------------------------------
ids = [f"P{1000 + i + 1}" for i in range(N)]
names = [f"{st} {sc} Package {i + 1}" for i, (st, sc) in enumerate(zip(state, sector))]  # clearly synthetic

df = pd.DataFrame({
    "project_id": ids,
    "project_name": names,
    "sector": sector,
    "state": state,
    "project_cost_cr": np.round(cost, 1),
    "planned_duration_months": duration,
    "months_elapsed": months_elapsed,
    "physical_progress_pct": np.round(progress, 1),
    "expenditure_pct": np.round(expenditure, 1),
    "contractor_experience_years": experience,
    "land_acquisition_required": land_required,
    "land_acquisition_pct": np.round(land_pct, 1),
    "delay_risk": (eventual_delay_frac > DELAY_THRESHOLD).astype(int),
})
truth = pd.DataFrame({"project_id": ids, "eventual_delay_frac": np.round(eventual_delay_frac, 4)})

# ----------------------------------------------------------------------------
# 6. Realism: a few missing values and extreme projects (documented in DATA_CARD)
# ----------------------------------------------------------------------------
df["contractor_experience_years"] = df["contractor_experience_years"].astype("Int64")
df.loc[rng.random(N) < 0.02, "contractor_experience_years"] = pd.NA     # ~2% missing
df.loc[rng.random(N) < 0.015, "expenditure_pct"] = np.nan               # ~1.5% missing
mega = rng.random(N) < 0.005                                            # ~0.5% mega-projects
df.loc[mega, "project_cost_cr"] = np.round(df.loc[mega, "project_cost_cr"] * 8, 1)


# ----------------------------------------------------------------------------
# 7. Validation: fail loudly if a logical rule is broken
# ----------------------------------------------------------------------------
def validate(d: pd.DataFrame) -> None:
    assert d["project_id"].is_unique, "duplicate project_id"
    assert not d.duplicated().any(), "duplicate rows"
    assert d["physical_progress_pct"].between(0, 100).all()
    assert d["expenditure_pct"].dropna().between(0, 100).all()
    assert d["land_acquisition_pct"].between(0, 100).all()
    assert (d["months_elapsed"] >= 1).all()
    assert (d["months_elapsed"] <= d["planned_duration_months"]).all(), "snapshot after deadline (D-009)"
    no_land = d["land_acquisition_required"] == 0
    assert (d.loc[no_land, "land_acquisition_pct"] == 100).all(), "land rule broken (D-007)"
    assert d["delay_risk"].isin([0, 1]).all()


if __name__ == "__main__":
    validate(df)
    out = Path(__file__).resolve().parent / "data"
    out.mkdir(exist_ok=True)
    df.to_csv(out / "infrastructure_projects.csv", index=False)
    truth.to_csv(out / "hidden_truth.csv", index=False)

    print(f"Saved {len(df)} projects to {out}")
    print(f"Delayed share (delay_risk=1): {df['delay_risk'].mean():.3f}")
    print("\nDelayed share by sector:")
    print(df.groupby("sector")["delay_risk"].agg(["count", "mean"]).round(3))
    stage = pd.cut(df["months_elapsed"] / df["planned_duration_months"], [0, 1 / 3, 2 / 3, 1.0],
                   labels=["early", "mid", "late"])
    print("\nDelayed share by stage:")
    print(df.groupby(stage, observed=True)["delay_risk"].agg(["count", "mean"]).round(3))
    print("\nMissing values:")
    print(df.isna().sum()[df.isna().sum() > 0])
