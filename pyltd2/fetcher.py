from copy import deepcopy
from typing import Iterable, Tuple
from warnings import warn
import numpy as np
import json
import pandas as pd
import os
from requests import get as GET
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

from .offset_iterator import OffsetIterator
from ._constants import SORTBY_DATE, SORT_ASCEND, FIRST_MATCH_DATE, QTYPE_NORM, MAX_OFFSET
from ._constants import MATCH, PLAYER, PARTY, FIGHTERS, ROLLS, SPELLS, KINGS_HPS, KINGS_UPGRADES, PLAYER_WAVES, MERCENARIES, LEAKS, BUILDS, DELTA_BUILDS
from .exceptions import EntryNotFoundError, ForbiddenError, LimitExceededError, RequestValueError, RequestError, WaitInterruptedError, TooManyRequestsError
from .utils import segmented_wait, simplify_version, builds_delta, place_fighters
from .logger import Log


class LTD2Fetcher:
    def __init__(self, api_key: str, version: str = None, limit: int = 50, offset: int = 0, sort_by: str = SORTBY_DATE,
                 sort_direction: int = SORT_ASCEND, date_after: datetime = FIRST_MATCH_DATE, date_before: datetime = datetime.now(),
                 include_details: bool = False, count_results: bool = False, queue_type: str = QTYPE_NORM,                 
                 match_filter_callback: callable = None, retry_on_fail: bool = True, retry_wait: int = 5, verbose: int = 0) -> None:
        """Fetches game data from the Legion TD 2's. 
        
        Used to perform a single HTTP request to the server and retrieve the data.
        The data can either be returned as a tuple of dictionaries or as a tuple of pd.DataFrames, 
        with each dictionary containing the corresponding type of data:
            matches
            spell choices
            kings HPs
        additional data if include_details is True:
            players
            parties
            fighters
            rolls
            kings upgrades
            player waves
            mercenaries
            leaks
            builds
        During initialization you can specify specific parameters for the request.

        Args:
            api_key (str): API Key used to perform the request.
            version (str, optional): Patch version of the match. Defaults to None.
            limit (int, optional): Maximum number of records to return. Defaults to 50.
            offset (int, optional): Number of records to skip for pagination. Defaults to 0.
            sort_by (str, optional): Sort games before fetching and limiting by this value. Defaults to date.
            sort_direction (int, optional): Specify sort direction. 1 is ASC, -1 is DESC. Defaults to ascending.
            date_after (datetime, optional): Return games that started after this date/time in UTC. Defaults to datetime(2018, 8, 3, 15, 39, 00).
            date_before (datetime, optional): Return games that started before this date/time in UTC (YYYY-MM-DD HH:MM:SS). Defaults to datetime.now().
            include_details (bool, optional): Include player specific match details. Defaults to False.
            count_results (bool, optional): Include the amount of entries for this query. Defaults to False.
            queue_type (str, optional): Queue type of the matches. Defaults to Normal.
            match_filter_callback (callable, optional): Callable to filter the matches fetched from the request. Must return True/False (keep/not to keep the match). Defaults to None.
            retry_on_fail (bool, optional): Whether or not to retry if the request fails. Defaults to True.
            retry_wait (int, optional): Seconds to wait before retrying the failed request. Defaults to 5.
            verbose (int, optional): Verbosity level. Will print messages for value >= 1. Defaults to 0.
        """
        self.matches_parsed_count = 0
        self.api_key = api_key
        self.version = version
        if limit > 50:
            limit = 50
            warn(f"limit parameter must be <= 50, got {limit}. Changing to 50.")
        self.limit = limit
        self.offset = offset
        self.sort_by = sort_by
        self.sort_direction = sort_direction
        self.date_after = date_after
        self.date_before = date_before
        self.include_details = include_details
        self.count_results = count_results
        self.queue_type = queue_type
        self.retry_on_fail = retry_on_fail
        self.retry_wait = retry_wait
        self.match_filter_callback = match_filter_callback
        self.verbose = verbose
        
        self._api_url_format = "https://apiv2.legiontd2.com/games"
        self._retry_count = 0
        self._max_retries = 5
        self._requests_count = 0
        self._requests_limit = 10_000
        
        self.full_builds = True
        self._unit_info = None
        self._upgrades_tree = None
    
    def _parse_matches(self, _matches: Iterable[dict]) -> Tuple[dict]:
        """Converts a list of matches returned from an HTTP request to a tuple of dictionaries containing
        each type of data.
        
        The parsing is performed according to the dictionaries in the data_acquisition module, where
        the expected data for each type of data are stored.

        Args:
            _matches (Iterable[dict]): List of matches returned from the HTTP request, each one in 
        a json format.

        Returns:
            tuple: Parsed data.
        """
        matches = deepcopy(MATCH)
        spells = deepcopy(SPELLS)
        kings_hps = deepcopy(KINGS_HPS)
        if self.include_details:
            players = deepcopy(PLAYER)
            parties = deepcopy(PARTY)
            fighters = deepcopy(FIGHTERS)
            rolls = deepcopy(ROLLS)
            kings_upgrades = deepcopy(KINGS_UPGRADES)
            players_waves = deepcopy(PLAYER_WAVES)
            mercenaries = deepcopy(MERCENARIES)
            leaks = deepcopy(LEAKS)
            builds = deepcopy(BUILDS) if self.full_builds else deepcopy(DELTA_BUILDS)
        
        for _match in _matches:
            match_id = _match["_id"]
            match_version = simplify_version(_match["version"])
            for match_key in matches.keys():
                if "side_won" == match_key: continue
                if _match.get(match_key, None) is None:
                    matches[match_key].append(None)
                else:
                    matches[match_key].append(_match[match_key])
            matches["side_won"].append(
                "right" if _match["leftKingPercentHp"][-1] == 0 else "left"
            )
            
            spells["_id"].append(match_id)
            for i in range(3):
                key = f"choice_{i+1}"
                spells[key].append(_match["spellChoices"][i])

            for i, (left_hp, right_hp) in enumerate(zip(_match["leftKingPercentHp"], _match["rightKingPercentHp"]), start=1):
                kings_hps["_id"].append(match_id)
                kings_hps["wave"].append(i)
                kings_hps["left_hp"].append(left_hp)
                kings_hps["right_hp"].append(right_hp)
            
            if self.include_details:
                for player in _match["playersData"]:
                    players["_id"].append(match_id)
                    for player_key in players.keys():
                        if "_id" == player_key: continue
                        if player.get(player_key, None) is None:
                            players[player_key].append(None)
                        else:
                            if player_key == "stayedUntilEnd":
                                players[player_key].append(
                                    bool(player[player_key])
                                )
                            else:
                                players[player_key].append(player[player_key])
                    
                    if len(player["partyMembersIds"]) > 1:
                        # solo players are considered a party of 1, so skip if so
                        parties["_id"].append(match_id)
                        for i in range(8):  # max size of party
                            key = f"member_{i+1}"
                            if i < len(player["partyMembersIds"]):
                                parties[key].append(
                                    player["partyMembersIds"][i]
                                )
                            else:
                                parties[key].append(None)
                            
                    player_id = player["playerId"]
                    fighters["_id"].append(match_id)
                    fighters["playerId"].append(player_id)
                    
                    player_fighters = player["fighters"].split(",")
                    for i, fighter_key in enumerate(fighters.keys()):
                        if fighter_key in ["_id", "playerId"]: continue
                        if i < len(player_fighters):
                            fighters[fighter_key].append(
                                player_fighters[i].strip()
                            )
                        else:
                            fighters[fighter_key].append(None)
                    
                    rolls["_id"].append(match_id)
                    rolls["playerId"].append(player_id)
                    player_rolls = player["rolls"].split(",")
                    for i, roll_key in enumerate(rolls.keys()):
                        if roll_key in ["_id", "playerId"]: continue
                        if i < len(player_rolls):
                            rolls[roll_key].append(
                                player_rolls[i].strip()
                            )
                        else:
                            rolls[roll_key].append(None)
                    
                    if player.get("kingUpgradesPerWave", None) is not None:
                        for i, wave_upgrades in enumerate(player["kingUpgradesPerWave"], start=1):
                            for seq_num, upgrade in enumerate(wave_upgrades, start=1):
                                kings_upgrades["_id"].append(match_id)
                                kings_upgrades["playerId"].append(player_id)
                                kings_upgrades["wave"].append(i)
                                kings_upgrades["upgrade"].append(upgrade)
                                kings_upgrades["seq_num"].append(seq_num)
                    
                    for i, (networth, workers, income) in enumerate(zip(player["netWorthPerWave"], player["workersPerWave"], player["incomePerWave"]), start=1):
                        players_waves["_id"].append(match_id)
                        players_waves["playerId"].append(player_id)
                        players_waves["wave"].append(i)
                        players_waves["networth"].append(networth)
                        players_waves["workers"].append(workers)
                        players_waves["income"].append(income)
                    
                    for i, wave_mercenaries in enumerate(player["mercenariesSentPerWave"], start=1):
                        for seq_num, mercenary in enumerate(wave_mercenaries, start=1):
                            mercenaries["_id"].append(match_id)
                            mercenaries["playerId"].append(player_id)
                            mercenaries["received"].append(True)
                            mercenaries["wave"].append(i)
                            mercenaries["mercenary"].append(mercenary)
                            mercenaries["seq_num"].append(seq_num)
                    
                    for i, wave_mercenaries in enumerate(player["mercenariesReceivedPerWave"], start=1):
                        for seq_num, mercenary in enumerate(wave_mercenaries, start=1):
                            mercenaries["_id"].append(match_id)
                            mercenaries["playerId"].append(player_id)
                            mercenaries["received"].append(False)
                            mercenaries["wave"].append(i)
                            mercenaries["mercenary"].append(mercenary)
                            mercenaries["seq_num"].append(seq_num)
                    
                    for i, wave_leaks in enumerate(player["leaksPerWave"], start=1):
                        for seq_num, leak in enumerate(wave_leaks, start=1):
                            leaks["_id"].append(match_id)
                            leaks["playerId"].append(player_id)
                            leaks["wave"].append(i)
                            leaks["unit"].append(leak)
                            leaks["seq_num"].append(seq_num)
                    
                    if self.full_builds:
                        for wave, wave_builds in enumerate(player["buildPerWave"], start=1):
                            for seq_num, build in enumerate(wave_builds, start=1):
                                builds["_id"].append(match_id)
                                builds["playerId"].append(player_id)
                                builds["wave"].append(wave)
                                fighter_info = build.split(":")
                                if match_version >= 9.06:
                                    fighter, coords, stacks = fighter_info
                                else:
                                    fighter, coords = fighter_info
                                    stacks = None
                                fighter = fighter.lower()
                                x, y = coords.split("|")
                                builds["fighter"].append(fighter)
                                builds["x"].append(x)
                                builds["y"].append(y)
                                builds["stacks"].append(stacks)
                                builds["seq_num"].append(seq_num)
                    else:
                        old_board = -np.ones((28, 18), dtype=int)
                        first_wave_builds = player["buildPerWave"][0]
                        for seq_num, build in enumerate(first_wave_builds, start=1):
                            fighter_info = build.split(":")
                            if match_version >= 9.06:
                                fighter, coords, stacks = fighter_info
                            else:
                                fighter, coords = fighter_info
                                stacks = None
                            # disabled units are skipped
                            if fighter not in self._unit_info.index: continue
                            x, y = coords.split("|")
                            builds["_id"].append(match_id)
                            builds["playerId"].append(player_id)
                            builds["wave"].append(1)
                            builds["fighter"].append(fighter)
                            builds["x"].append(x)
                            builds["y"].append(y)
                            builds["stacks"].append(stacks)
                            builds["seq_num"].append(seq_num)
                            builds["action"].append("Placed")
                        old_board = place_fighters(old_board, first_wave_builds, self._unit_info)

                        for wave, wave_builds in enumerate(player["buildPerWave"], start=1):
                            new_board = -np.ones((28, 18), dtype=int)
                            new_board = place_fighters(new_board, wave_builds, self._unit_info)
                            
                            delta = builds_delta(old_board, new_board, self._upgrades_tree, self._unit_info)
                            for seq_num, (fighter, x, y, action) in enumerate(delta, start=1):
                                builds["_id"].append(match_id)
                                builds["playerId"].append(player_id)
                                builds["wave"].append(wave)
                                builds["fighter"].append(fighter)
                                builds["x"].append(x)
                                builds["y"].append(y)
                                if match_version >= 9.06 and action != "Sold":
                                    if x % 1 == 0:
                                        x = int(x)
                                    if y % 1 == 0:
                                        y = int(y)
                                    wave_flags = [
                                        f"{fighter}:{x}|{y}" in build
                                        for build in wave_builds
                                    ]
                                    stack_index = np.where(wave_flags)[0][0]
                                    _, _, stacks = wave_builds[stack_index].split(":")
                                else:
                                    stacks = None
                                builds["stacks"].append(stacks)
                                builds["action"].append(action)
                                builds["seq_num"].append(seq_num)
                            old_board = new_board.copy()
        
        if self.include_details:
            return (matches, spells, kings_hps, players, parties, fighters, \
                rolls, kings_upgrades, players_waves, mercenaries, leaks, builds)
        else:
            return (matches, spells, kings_hps)
    
    def get(self, return_as_df=False) -> tuple:
        """Performs an HTTP request and returns the parsed data.
        
        The request's parameters are defined during the initialization of the class.
        If the request fails, it will try to perform the request after retry_wait seconds,
        with a maximum of 5 retries. If it fails, None is returned.

        Args:
            return_as_df (bool, optional): Whether to return the data as a pd.DataFrame. Defaults to False.

        Returns:
            Tuple[dict]: Tuple containing the data as dictionaries if return_as_df = False.
            Tuple[pd.DataFrame]: Tuple containing the data as pd.DataFrame if return_as_df = True.
        """
        if self._retry_count >= self._max_retries:
            return None
        
        url = self._api_url_format.format(self.api_key)
        header = {
            "x-api-key": self.api_key,
        }
        request_params = {
            "version": self.version,
            "limit": self.limit,
            "offset": self.offset,
            "sortBy": self.sort_by,
            "sortDirection": self.sort_direction,
            "dateAfter": self.date_after,
            "dateBefore": self.date_before,
            "includeDetails": str(self.include_details).lower(),
            "countResults": str(self.count_results).lower(),
            "queueType": self.queue_type
        }
        
        if self.verbose >= 1:
            Log.info("Getting games", log_id=1)
        
        try:
            self._requests_count += 1
            response = GET(url, headers=header, params=request_params)
        except ConnectionError as err:
            if self.retry_on_fail:
                try:
                    segmented_wait(self.retry_wait)
                except WaitInterruptedError:
                    return None
                
                self.retry_count += 1
                if self.retry_count == self._max_retries:
                    raise RequestError(f"Connection error {err}.")
                
                return self.get(return_as_df=return_as_df)
            else:
                return None
        
        data = response.json()
        
        if isinstance(data, dict):
            response_message = data.get("message", None)
            if response_message is not None and response_message == "Forbidden":
                raise ForbiddenError(f"Invalid API key provided ({self.api_key}).")
            
            response_error = data.get("err", None)
            if response_error is not None:
                if response_error == "Entry not found.":
                    raise EntryNotFoundError(f"""Entry not found.\n
                                            Request parameters: {json.dumps({k: str(v) for k, v in request_params.items()}, indent=4)}""")
                else:
                    error_value = response_error[0]
                    error_type = error_value["keyword"]
                    if "exceeded" in error_value["message"].lower():
                        raise LimitExceededError("Request limit exceeded.")
                    elif error_type == "type":
                        parameter_name = error_value["instancePath"].split("/")[-1]
                        raise RequestValueError(f"Invalid value for parameter {parameter_name}.")
        
        if response.status_code == 429:
            # server still returns 429 sometimes when request limits is reached
            if self._requests_count < self._requests_limit:
                raise LimitExceededError("Request limit exceeded.")
            else:
                raise TooManyRequestsError()
        elif response.status_code != 200:
            if self.retry_on_fail:
                try:
                    segmented_wait(self.retry_wait)
                except WaitInterruptedError:
                    return None
                
                self.retry_count += 1
                if self.retry_count == self._max_retries:
                    raise RequestError(f"Response status code {response.status_code}.")
                
                return self.get(return_as_df=return_as_df)
            else:
                return None
        else:
            self.retry_count = 0
            if self.verbose >= 1:
                Log.info("Received results. Parsing...", log_id=1)
            matches = data
            matches = [
                match
                for match in matches
                if match["gameLength"] > 0
            ]
            if self.match_filter_callback is not None:
                matches = [
                    match
                    for match in matches
                    if self.match_filter_callback(match)
                ]
            matches_count = len(matches)
            if self.verbose >= 1:
                Log.info(f"{matches_count} found", append_last=True, log_id=1)
            self.matches_parsed_count += matches_count
            parsed_matches = self._parse_matches(matches)
            if return_as_df:
                return [pd.DataFrame(data) for data in parsed_matches]
            else:
                return parsed_matches
    
    def set_options(self, full_builds: bool=None) -> None:
        """
        Sets fetcher options.

        Args:
            full_builds (bool, optional): 
                If True, all the builds per wave are saved fully.
                If False, only the changes per wave are saved.

        Raises:
            TypeError: 
                if full_builds is not a boolean value.
        """
        if full_builds is not None:
            if type(full_builds) is not bool:
                raise TypeError("full_builds must be boolean")
            self.full_builds = full_builds
            if not self.full_builds:
                Log.warning("This option requires unit info to be downloaded.")
                from _constants import UNIT_INFO_URL, UNIT_UPGRADES_TREE_URL
                self._unit_info = pd.read_csv(UNIT_INFO_URL)
                self._upgrades_tree = json.loads(
                    GET(UNIT_UPGRADES_TREE_URL).text
                )
                Log.info("Finished downloading additional data.")
                self._unit_info.set_index("unitId", inplace=True)

        
class ExhaustiveFetcher:
    def __init__(self, destination_directory: str, fetcher: LTD2Fetcher = None, save_interval: int = 500, verbose:int = 0, **filenames) -> None:
        """Exhaustive fetch of data from Legion TD 2's servers that saves the data to csv files.
        
        ExchaustivFetcher uses an LTD2Fetcher object to perform the requests and saves the 
        different types of data to csv files in the destination_directory folder.
        You can specify specific names for each file by using the kwargs parameters, which
        basically is a translation of the original filenames to the desired ones.
        Original filenames:
            matches
            spell choices
            kings HPs
        if include_details in LTD2Fetcher is True:
            players
            parties
            fighters
            rolls
            kings upgrades
            player waves
            mercenaries
            leaks
            builds

        Args:
            destination_directory (str): Directory where to save the csv data files.
            fetcher (LTD2Fetcher, optional): Can be provided manually for custom request parameters. Defaults to LTD2Fetcher.
            save_interval (int, optional): Frequency with which to save the fetched data, with respect to the offset value. Defaults to 500.
            verbose (int, optional): Verbosity level. Will print messages for value >= 1. Defaults to 0.

        Raises:
            TypeError: In case a non-LTD2Fetcher parameter value is provided.
        """
        self.destination_dir = destination_directory
        Path(self.destination_dir).mkdir(parents=True, exist_ok=True)
        self._call_wait = 1.
        self.save_interval = save_interval
        self.verbose = verbose
        
        if fetcher is None:
            self.fetcher = LTD2Fetcher(verbose=verbose)
        else:
            if not isinstance(fetcher, LTD2Fetcher):
                raise TypeError("fetcher parameter should be an instance of LTD2Fetcher.")
            self.fetcher = fetcher
        
        self.last_match_date = self.fetcher.date_after
        self._days_diff = (self.fetcher.date_before - self.fetcher.date_after).days + 1
        if self.verbose > 0:
            self._progress_bar = tqdm(range(self._days_diff), desc="Fetching games", total=self._days_diff, unit="day")
        
        self._data_templates = [
            MATCH,
            SPELLS,
            KINGS_HPS,
            PLAYER,
            PARTY,
            FIGHTERS,
            ROLLS,
            KINGS_UPGRADES,
            PLAYER_WAVES,
            MERCENARIES,
            LEAKS,
            BUILDS if getattr(self.fetcher, "full_builds", True) else DELTA_BUILDS
        ]
        
        self.data = [
            []
            for _ in self._data_templates
        ]
        # TODO: Improve readability and still keep it short
        self.filepaths = (
            os.path.join(self.destination_dir, filenames.get('matches', 'matches') + ".csv"),
            os.path.join(self.destination_dir, filenames.get('spell_choices', 'spell_choices') + ".csv"),
            os.path.join(self.destination_dir, filenames.get('kings_hps', 'kings_hps') + ".csv"),
            os.path.join(self.destination_dir, filenames.get('players', 'players') + ".csv"),
            os.path.join(self.destination_dir, filenames.get('parties', 'parties') + ".csv"),
            os.path.join(self.destination_dir, filenames.get('fighters', 'fighters') + ".csv"),
            os.path.join(self.destination_dir, filenames.get('rolls', 'rolls') + ".csv"),
            os.path.join(self.destination_dir, filenames.get('kings_upgrades', 'kings_upgrades') + ".csv"),
            os.path.join(self.destination_dir, filenames.get('player_waves', 'player_waves') + ".csv"),
            os.path.join(self.destination_dir, filenames.get('mercenaries', 'mercenaries') + ".csv"),
            os.path.join(self.destination_dir, filenames.get('leaks', 'leaks') + ".csv"),
            os.path.join(self.destination_dir, filenames.get('builds', 'builds') + ".csv"),
        )
        self._original_filenames = ["matches", "spell_choices", "kings_hps", "players", "parties", "fighters", "rolls", "kings_upgrades", "player_waves", "mercenaries", "leaks", "builds"]
        self._file_translations = {
            original_filename: filenames.get(original_filename, original_filename)
            for original_filename in self._original_filenames
        }
        if not self.fetcher.include_details:
            # if details should not be included then the API only returns data for matches, spells and kings' hp
            self.data = self.data[:3]
            self.filepaths = self.filepaths[:3]
    
    def _update_data(self, _parsed_data: Iterable[dict]) -> None:
        """Updates the data dictionaries.

        Args:
            _parsed_data (Iterable[dict]): Data fetched from a request.
        """
        for data_i, _data in enumerate(_parsed_data):
            self.data[data_i].append(_data)
        last_date_str = self.data[0][-1]["date"].values[-1]
        self.last_match_date = datetime.fromisoformat(last_date_str[:-1])
        
    def _append_or_create(self, data: pd.DataFrame, filepath: str) -> None:
        """Appends data to an existing csv file or creates a new one.

        Args:
            data (pd.DataFrame): DataFrame of the data.
            path (str): Where to create or update the csv file.
        """
        if os.path.exists(filepath):
            data.to_csv(filepath, mode="a", header=False, index=False)
        else:
            data.to_csv(filepath, index=False)
    
    def _save_history(self) -> None:
        """Calls _append_or_create for all the different types of data.
        """
        if self.verbose > 0:
            self._progress_bar.set_description("Updating files.")
        for _data, filepath in zip(self.data, self.filepaths):
            if len(_data) > 0:
                df = pd.concat(_data, axis=0)
                self._append_or_create(df, filepath)
        self.data = [
            []
            for _ in self._data_templates
        ]
        if not self.fetcher.include_details:
            self.data = self.data[:3]
        
        if self.verbose > 0:
            self._progress_bar.set_description("Done updating files")
    
    def start_fetching(self) -> None:
        """Starts fetching match data for the provided date_after and date_before parameters in fetcher.
        
        Performs the requests to collect data for all the matches that were played from the date_before
        until the date_after dates in the LTD2Fetcher provided during initilization.
        Only catches LimitExceededError exception, saving the progress to the files and exits.
        In case the maximum offset is reached, it automatically updates the date_after attribute
        of LTD2Fetcher to continue fetching.
        """
        offset_generator = OffsetIterator(step_size=self.fetcher.limit)
        while True:
            try:
                match_history = self.fetcher.get(return_as_df=True)
                current_days_diff = (self.fetcher.date_before - self.last_match_date).days
                if self.verbose > 0:
                    if current_days_diff < self._days_diff:
                        self._progress_bar.update()
                        self._days_diff = current_days_diff
                    else:
                        self._progress_bar.update(0)
            except EntryNotFoundError as e:
                if len(self.data[0]):
                    if self.verbose > 0:
                        self._progress_bar.set_description("Done")
                    self._save_history()
                    break
                else:
                    Log.important(e)
                    break
            except LimitExceededError:
                Log.important("Request limit exceeded.")
                self._save_history()
                break
            except TooManyRequestsError:
                Log.important("Too many requests performed. Waiting for 10 seconds.")
                try:
                    segmented_wait(10)
                except WaitInterruptedError:
                    self._save_history()
                    break
                continue
            except KeyboardInterrupt:
                Log.important("Fetching interrupted.")
                self._save_history()
                break
            
            if match_history is not None:
                self._update_data(match_history)
            
            if self.last_match_date >= self.fetcher.date_before:
                self._save_history()
                if self.verbose > 0:
                    self._progress_bar.set_description("Done")
                    self._progress_bar.update()
                break
            
            if int(offset_generator.current) >= self.save_interval and \
                int(offset_generator.current) % self.save_interval == 0:
                self._save_history()
            
            if self.verbose > 0:
                self._progress_bar.set_description("Waiting...")
            
            try:
                segmented_wait(self._call_wait)
            except WaitInterruptedError:
                self._save_history()
                break
            
            _, offset_end = offset_generator()
            if int(offset_end) >= MAX_OFFSET:
                offset_end = offset_generator.reset()
                self._save_history()
                self.fetcher.date_after = self.last_match_date
            
            self.fetcher.offset = offset_end
        
        print("")
        Log.info(f"Total requests: ({self.fetcher.matches_parsed_count} matches collected)", log_id=3)
        Log.info(f"Last date: {self.last_match_date}", log_id=4)
        return self.last_match_date