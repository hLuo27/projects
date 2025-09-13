import os
import sys
import pandas as pd
from tqdm import tqdm
import sportsipy.nhl.schedule as nhl_schedule
from sportsipy.nhl.teams import Teams
import time
from typing import Dict
import polars as pl
import pytz

base_dir = (os.path.join(os.path.dirname(__file__), '../').replace("\\", "/").replace("src/../", "")
            .replace("etl/../", "")
            )
sys.path.insert(1, base_dir)

import src.utils as utils

eastern_tz = pytz.timezone("America/Toronto")


def get_nhl_game_details(g: nhl_schedule.Game) -> Dict:
    """
    Get details for a single NHL game
    :param g: nhl_schedule.Game
    :return: dict
    """
    g_boxscore = g.boxscore
    dict_g = {'boxscore_index': g.boxscore_index,
              'Date': g.date,
              'Time': g_boxscore.time,
              'Duration': g_boxscore.duration,
              'Opponent': g.opponent_abbr,
              'Location': g.location,
              'Arena': g_boxscore.arena,
              'Attendance': g.boxscore.attendance,
              'Result': g.result,
              'Corsi %': g.corsi_for_percentage,
              'Fenwick %': g.fenwick_for_percentage,
              'PDO': g.pdo,
              'Goals': g.goals_scored,
              'Opponent Goals': g.goals_allowed,
              'Shots': g.shots_on_goal,
              'Opponent Shots': g.opp_shots_on_goal,
              'PIM': g.penalties_in_minutes,
              'Opponent PIM': g.opp_penalties_in_minutes,
              }
    return dict_g


def pull_nhl_schedule(team_abbr: str, year: int) -> pl.DataFrame:
    """
    Pull hockey-reference schedule data for a specific team
    :param team_abbr: str
    :param year: int
    :return: pl.DataFrame
    """
    cache_filepath_raw = f"{base_dir}data/sportsipy/nhl_{team_abbr}_{year}.csv"
    if not os.path.exists(cache_filepath_raw):
        utils.logger.info(f"Cached sportsipy data not found at {cache_filepath_raw} - now re-pulling")
        all_games = utils.safe_execute(nhl_schedule.Schedule,
                                       log_id=f'SCHEDULE {team_abbr}',
                                       max_retries=5,
                                       sleep_time=60 * 30,  # retry after 30mins since we got a 429 retry after 60mins
                                       abbreviation=team_abbr,
                                       year=year,
                                       )

        df_games = []
        for g in tqdm(all_games):
            dict_g = utils.safe_execute(get_nhl_game_details,
                                        log_id=f'GAME LOG {team_abbr} | GAME {list(all_games).index(g) + 1}',
                                        max_retries=5,
                                        sleep_time=60 * 30,  # retry after 30mins since we got a 429 retry after 60mins
                                        g=g,
                                        )
            time.sleep(10)
            df_games += [dict_g]

        df_games = pd.DataFrame(df_games)
        df_games.to_csv(cache_filepath_raw, index=False)

    df_games = pl.scan_csv(cache_filepath_raw).collect()
    return df_games


def pull_nhl_schedule_all(year: int) -> pl.DataFrame:
    """
    Pull all schedule data for NHL teams in a year
    :param year: int
    :return: pl.DataFrame
    """
    all_teams = Teams(year)
    utils.logger.info(f"Pulling schedules for {len(all_teams)} NHL teams in {year}")

    df_schedule_all = []
    for t in tqdm(all_teams):
        df_schedule_t = pull_nhl_schedule(t.abbreviation, year)
        if not df_schedule_t.is_empty():
            df_schedule_all += [df_schedule_t]

    if len(df_schedule_all) > 0:
        return pl.concat(df_schedule_all)
    else:
        utils.logger.warning(f"No schedules found for any NHL teams in {year}")
        return pl.DataFrame()
