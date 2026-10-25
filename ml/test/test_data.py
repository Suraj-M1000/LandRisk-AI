import pytest
import pandas as pd
from pathlib import Path
import hashlib
import subprocess
import sys



ROOT = Path(__file__).resolve().parents[1]          # repo root (the folder above tests/)
SCRIPT = ROOT / "ml" / "generate_data.py"
CSV = ROOT / "ml" / "data" / "infrastructure_projects.csv"

EXPECTED_COLUMNS = [
    "project_id", "project_name", "sector", "state", "project_cost_cr",
    "planned_duration_months", "months_elapsed", "physical_progress_pct",
    "expenditure_pct", "contractor_experience_years", "land_acquisition_required",
    "land_acquisition_pct", "delay_risk",
]

def run_generator() -> None:
    """Run generate_data.py exactly as you would in the terminal."""
    # sys.executable = the Python running pytest (so the same virtual environment is used)
    # check=True = raise an error if the script crashes, which fails the test
    subprocess.run([sys.executable, str(SCRIPT)], check=True, cwd=ROOT, capture_output=True)


def file_hash(path: Path) -> str:
    """A fingerprint of a file: identical content gives an identical hash."""
    return hashlib.sha256(path.read_bytes()).hexdigest()

@pytest.fixture(scope="module")
def df() -> pd.DataFrame:
    """
    A fixture is set-up code that pytest runs once and hands to every test that
    asks for it by name. scope="module" = build it once for this whole file.
    """
    run_generator()                                  # always test freshly generated data
    return pd.read_csv(CSV)

def test_columns_exact(df):
    assert list(df.columns) == EXPECTED_COLUMNS



def test_row_count(df):
    assert len(df) == 2000


def test_ids_unique_and_no_duplicate_rows(df):
    assert df["project_id"].is_unique
    assert not df.duplicated().any()

def test_experience_in_plausible_range(df):
    assert df["contractor_experience_years"].dropna().between(1, 30).all()


def test_snapshot_before_deadline(df):               # decision D-009
    assert (df["months_elapsed"] <= df["planned_duration_months"]).all()

def test_target_is_binary(df):
    assert set(df["delay_risk"].unique()) == {0, 1}


def test_delayed_share_reasonable(df):
    share = df["delay_risk"].mean()
    assert 0.20 <= share <= 0.50, f"delayed share {share:.3f} is outside 20-50%"


def test_missing_values_only_where_expected(df):
    missing = df.isna().sum()
    allowed = {"expenditure_pct", "contractor_experience_years"}
    unexpected = set(missing[missing > 0].index) - allowed
    assert not unexpected, f"unexpected missing values in: {unexpected}"
    assert (missing / len(df) < 0.05).all()          # never more than 5% missing


def test_generator_is_reproducible():
    run_generator()
    first = file_hash(CSV)
    run_generator()
    second = file_hash(CSV)
    assert first == second, "same seed produced different files"