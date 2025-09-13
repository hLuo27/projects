import logging
from typing import List, Callable, Any
import pandas as pd
import pytz
from datetime import datetime, timezone
import time

logging.basicConfig(format="%(asctime)s [%(filename)s:%(lineno)d] [%(levelname)s] %(message)s",
                    handlers=[logging.StreamHandler()])
logger = logging.getLogger()
logger.setLevel(logging.INFO)


class MaxRetriesExceededError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


def move_cols(df: pd.DataFrame, preceding_col: str, cols_to_move: List[str]) -> pd.DataFrame:
    """
    Helper function to move cols_to_move to the right of df[preceding_col]
    :param df: pd.DataFrame
    :param preceding_col: str
    :param cols_to_move: List[str]
    :return: pd.DataFrame
    """
    if preceding_col not in df.columns:
        raise ValueError(f"Missing preceding column {preceding_col} in df: {df.columns}")

    missing_cols = set(cols_to_move) - set(df.columns)
    if len(missing_cols) > 0:
        logger.warning(f"Tried to move columns that are missing in df: {missing_cols}")
        cols_to_move = [col for col in cols_to_move if col not in missing_cols]

    col_list = df.columns.tolist()
    preceding_index = col_list.index(preceding_col)

    # remove columns from col_list first
    for col in cols_to_move:
        col_list.pop(col_list.index(col))

    # then insert in correct position
    for i, col in enumerate(cols_to_move):
        col_list.insert(preceding_index + 1 + i, col)

    return df[col_list]


def convert_utc(s: pd.Series) -> pd.Series:
    """
    Helper function to convert timestamp UTC like 1420473399 -> 2015-01-05 10:56:39
    :param s: pd.Series[int]
    :return: pd.Series[datetime]
    """
    return (pd.to_datetime(s, unit='s')
            .dt.tz_localize(pytz.utc)
            .dt.tz_convert(pytz.timezone('US/Eastern'))
            .dt.tz_localize(None)  # remove time zone so we can export to Excel
            )


def convert_to_utc_timestamp(date_str: str) -> int:
    """
    Takes a date in ET and converts it to a Unix UTC timestamp.
    :param date_str: str - Date string in the format YYYY-MM-DD
    :return: int - Unix timestamp in UTC
    """
    # convert to datetime
    local_dt = datetime.strptime(date_str, "%Y-%m-%d")

    # add ET info
    eastern = pytz.timezone("America/New_York")
    et_dt = eastern.localize(local_dt)

    # convert to UTC and replace int
    utc_dt = et_dt.astimezone(timezone.utc)
    return int(utc_dt.timestamp())


def safe_execute(func: Callable[..., Any], log_id: str, max_retries: int, sleep_time: int, **kwargs: Any) -> Any:
    """
    Tries to execute a given function func(**kwargs) up to max_retries attempts, pausing sleep_time between each
    attempt and displaying logger messages using log_id
    :param func: The function to be executed.
    :param log_id: A string identifier for logging.
    :param max_retries: Number of retries before giving up.
    :param sleep_time: Time to sleep between retries.
    :param kwargs: Keyword arguments to pass to `func`.
    :return: The result of `func` if successful, or None if all retries fail.
    """
    for i in range(max_retries):
        try:
            return func(**kwargs)
        except Exception as e:
            if i < (max_retries - 1):
                logger.warning(f"{log_id} ATTEMPT {i + 1}/{max_retries}: Got error {e}, pausing for {sleep_time} "
                               f"seconds before re-attempting")
                time.sleep(sleep_time)
            else:
                raise MaxRetriesExceededError(f"{log_id}: Max retries exceeded with error {e}")
