# rules.py
from datetime import datetime
from typing import Optional
from typing import cast

import pandas as pd

def check_kyc_status(
    kyc_status: str,
    id_expiry: Optional[pd.Timestamp],
    today: Optional[pd.Timestamp] = None
) -> str:
    """
    Returns:
      - 'INCOMPLETE' if kyc_status != 'complete'
      - 'EXPIRED'   if kyc_status == 'complete' but id_expiry < today
      - 'OK'        otherwise
    """
    # If caller didn’t supply a 'today', use today’s date
    if today is None:
        today = pd.to_datetime(datetime.today().date())

    if kyc_status.lower() != 'complete':
        return 'INCOMPLETE'

    # If expiry is missing or before today, it’s expired
    if id_expiry is None or pd.isna(id_expiry) or id_expiry < today:
        return 'EXPIRED'

    return 'OK'


def flag_high_value(txn_amount: float, threshold: float) -> str:
    """
    Returns 'ALERT' if txn_amount > threshold, else 'OK'.
    """
    return 'ALERT' if txn_amount > threshold else 'OK'


def compute_txns_last_window(
    txn_times: pd.Series,
    window: str
) -> pd.Series:
    """
    For each timestamp in txn_times, count how many transactions
    occurred in the preceding `window` (e.g. '1H').
    """
    # 1) Parse to datetime
    times = pd.to_datetime(txn_times, errors='coerce')
    window = window.lower()

    # 2) Build a Series of ones, indexed by timestamp
    s = pd.Series(1, index=times).sort_index()

    # 3) Sum those ones over the rolling window; result is counts per timestamp
    counts = s.rolling(window).sum().fillna(0).astype(int)

    # 4) Map counts back to the original order of txn_times
    result = [ counts.get(ts, 0) for ts in times ]

    # Return as a pd.Series so downstream code stays the same
    return pd.Series(result, name='txns_last_window')


def compute_frequency_flag(
    txns_last_window: pd.Series,
    limit: int
) -> pd.Series:
    """
    Returns a Series of 'ALERT'/'OK' based on whether the per-window
    transaction count >= limit.
    """
    return txns_last_window.apply(lambda cnt: 'ALERT' if cnt >= limit else 'OK')


def aggregate_agent_risk(df: pd.DataFrame) -> pd.DataFrame:
    """
    Given a DataFrame with columns:
      ['agent_id','kyc_flag','aml_flag','frequency_flag']
    returns a DataFrame:
      ['agent_id','risk_status']
    where risk_status is:
      - 'RED'    if any EXPIRED/ALERT flags
      - 'YELLOW' if any INCOMPLETE but no RED
      - 'GREEN'  otherwise
    """
    def _agent_risk(group):
        # Any red-level flags?
        if (
            (group['kyc_flag'] == 'EXPIRED').any() or
            (group['aml_flag'] == 'ALERT').any() or
            (group['frequency_flag'] == 'ALERT').any()
        ):
            return 'RED'
        # Any incomplete KYCs?
        if (group['kyc_flag'] == 'INCOMPLETE').any():
            return 'YELLOW'
        return 'GREEN'

    df2 = df.set_index('agent_id')
    risks = df2.groupby(level=0).apply(_agent_risk)
    return risks.reset_index(name='risk_status')
