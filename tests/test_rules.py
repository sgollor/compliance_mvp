# tests/test_rules.py
import pandas as pd
import pytest
from datetime import datetime, timedelta
from compliance_mvp.rules import (
    check_kyc_status,
    flag_high_value,
    compute_txns_last_window,
    compute_frequency_flag,
    aggregate_agent_risk
)


def test_check_kyc_status_incomplete():
    # not complete
    assert check_kyc_status('incomplete', pd.Timestamp('2030-01-01')) == 'INCOMPLETE'

def test_check_kyc_status_expired():
    # expired date
    today = pd.to_datetime('2025-07-10')
    assert check_kyc_status('complete', pd.Timestamp('2025-07-09'), today) == 'EXPIRED'

def test_check_kyc_status_ok():
    today = pd.to_datetime('2025-07-10')
    assert check_kyc_status('complete', pd.Timestamp('2025-07-11'), today) == 'OK'

@pytest.mark.parametrize("amt, threshold, expected", [
    (500,   1000, 'OK'),
    (1000,  1000, 'OK'),
    (1000.1,1000, 'ALERT'),
])
def test_flag_high_value(amt, threshold, expected):
    assert flag_high_value(amt, threshold) == expected

def test_compute_txns_last_window_basic():
    # timestamps one hour apart
    base = datetime(2025,7,10,10,0)
    times = pd.Series([
        pd.Timestamp(base),
        pd.Timestamp(base + timedelta(minutes=30)),
        pd.Timestamp(base + timedelta(minutes=90))
    ])
    counts = compute_txns_last_window(times, '1H')
    # at idx 0: only itself, at idx 1: two, at idx 2: only itself
    assert list(counts) == [1, 2, 1]

def test_compute_frequency_flag():
    counts = pd.Series([1,2,3,4])
    flags = compute_frequency_flag(counts, 3)
    assert list(flags) == ['OK','OK','ALERT','ALERT']

def test_aggregate_agent_risk():
    df = pd.DataFrame([
        {'agent_id':'A','kyc_flag':'OK','aml_flag':'OK','frequency_flag':'OK'},
        {'agent_id':'A','kyc_flag':'OK','aml_flag':'ALERT','frequency_flag':'OK'},
        {'agent_id':'B','kyc_flag':'INCOMPLETE','aml_flag':'OK','frequency_flag':'OK'},
        {'agent_id':'C','kyc_flag':'OK','aml_flag':'OK','frequency_flag':'ALERT'},
        {'agent_id':'D','kyc_flag':'OK','aml_flag':'OK','frequency_flag':'OK'},
    ])
    summary = aggregate_agent_risk(df)
    result = dict(zip(summary['agent_id'], summary['risk_status']))
    assert result == {
        'A':'RED',    # had an AML ALERT
        'B':'YELLOW', # had an INCOMPLETE
        'C':'RED',    # had a frequency ALERT
        'D':'GREEN'   # all OK
    }
