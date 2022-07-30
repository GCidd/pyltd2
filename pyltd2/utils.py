from time import sleep
from typing import List, Tuple
import numpy as np
from pandas import DataFrame

from .exceptions import WaitInterruptedError

def segmented_wait(wait_time: int) -> None:
    """
    Similar to time.sleep but waits every 0.1 seconds.

    Args:
        wait_time (int): 
            Time to wait for.

    Raises:
        WaitInterruptedError:
            If the wait loop is interrupted (KeyboardInterrupt).
    """
    try:
        for _ in np.arange(0, wait_time + 0.1, 0.1):
            sleep(0.1)
    except KeyboardInterrupt:
        raise WaitInterruptedError()

def simplify_version(version: str) -> float:
    """
    Simplifies version of a match.
    For example: v9.02b -> 9.02

    Args:
        version (str):
            Version string.

    Returns:
        float: 
            Version in float type.
    """
    # skip first char ('v') -> split on '.' -> take first 2 parts -> join with '.' -> keep minor until minor version
    return float(
        ".".join(
            version[1:].split(".")[:2]
        )[:4]
    )


def place_fighters(board: np.ndarray, builds: List[str], unit_info: DataFrame) -> np.ndarray:
    """
    Places fighters on an array (representing the game's board).
    Fighter ids (from the game's server) are firstly converted to integer IDs according to
    unit_info.

    Args:
        board (numpy array): 
            A numpy array of (28, 18) shape, representing the player's board.
        builds (List[str]):
            List of units that are placed on the board in the following format:
                "unit_id:x|y"
        unit_info (DataFrame):
            Unit information as received from the repo or the game's server in a DataFrame structure.

    Returns:
        np.ndarray:
            The board with the fighters placed.
    """
    board = board.copy()
    for build in builds:            
        fighter, coords = build.split(":")[:2]
        fighter = fighter.lower()
        # disabled (in-game) units are skipped
        if fighter not in unit_info.index: continue
        fighter = fighter.lower()
        x, y = coords.split("|")
        y = int(float(y) * 2)
        x = int(float(x) * 2)
        board[y, x] = unit_info.id[fighter]
    return board


def _apply_condition(board:np.ndarray, mask: np.ndarray, action: str, unit_info: dict) -> List[Tuple[str, float, float, str]]:
    """
    Returns the actions applied on the fighters on the masked board.

    Args:
        board (np.ndarray): 
            A numpy array of (28, 18) shape, representing the player's board.
        mask (np.ndarray): 
            Boolean mask indicated which places on the board to return the actions for.
        action (str):
            The action that was taken.
        unit_info (dict): 
            Unit information as received from the repo or the game's server in a DataFrame structure.
    Returns:
        List[Tuple[str, float, float, str]]:
            A list of tuples containing the following data:
                (fighter_id, x, y, action)
    """
    deltas = []
    idxs = np.where(mask)
    if len(idxs[0]):
        fighter_ids = board[
            idxs[0], 
            idxs[1]
        ].flatten()
        fighters = unit_info.index[fighter_ids]
        xs = np.array(idxs[1]) / 2
        ys = np.array(idxs[0]) / 2
        deltas += list(zip(fighters, xs, ys, [action] * len(xs)))
    return deltas


def get_base_unit(unit_id: str, upgrades_tree: dict) -> str:
    """
    Finds the initial base unit of the unit_id.

    Args:
        unit_id (str):
            The unit for which to find its base unit.
        upgrades_tree (dict):
            The upgrades tree of all the units.

    Returns:
        str:
            The unit's id.
    """
    for base_unit_id, upgrades_unit_id in upgrades_tree.items():
        if unit_id in upgrades_unit_id:
            return base_unit_id
    return None


def builds_delta(board1: np.ndarray, board2: np.ndarray, upgrades_tree: dict, unit_info: DataFrame) -> List[Tuple[str, float, float, str]]:
    """
    Calculates the actions that need to be taken in order to go from board1 to board2.
    
    Args:
        board1 (np.ndarray):
            A numpy array of (28, 18) shape, representing the player's board.
        board2 (np.ndarray): 
            A numpy array of (28, 18) shape, representing the player's board.
        upgrades_tree (dict): 
            The upgrades tree of all the units.
        unit_info (DataFrame): 
            Unit information as received from the repo or the game's server in a DataFrame structure.

    Returns:
        List[Tuple[str, float, float, str]]: 
            A list of tuples containing the following data:
                (fighter_id, x, y, action)
    """
    deltas = []
    deltas += _apply_condition(
        board1,
        (board1 > -1)
        &
        (board2 == -1),
        "Sold",
        unit_info
    )
    deltas += _apply_condition(
        board2,
        (board1 == -1)
        &
        (board2 > -1),
        "Placed",
        unit_info
    )
    
    replaced_indxs = np.where(
        (board1 > -1)
        &
        (board2 > -1)
        &
        (board1 != board2)
    )
    if len(replaced_indxs[0]):
        prev_fighter_ids = board1[
            replaced_indxs[0],
            replaced_indxs[1]
        ].flatten()
        new_fighter_ids = board2[
            replaced_indxs[0],
            replaced_indxs[1]
        ].flatten()
        replaced_xs = replaced_indxs[1]
        replaced_ys = replaced_indxs[0]
        for prev_fighter_id, new_fighter_id, x, y in zip(prev_fighter_ids, new_fighter_ids, replaced_xs, replaced_ys):
            if get_base_unit(prev_fighter_id, upgrades_tree) == get_base_unit(new_fighter_id, upgrades_tree):
                deltas.append((
                    unit_info.index[new_fighter_id],
                    x / 2,
                    y / 2,
                    "Upgraded"
                ))
            else:
                deltas.append((
                    unit_info.index[prev_fighter_id],
                    x / 2,
                    y / 2,
                    "Sold"
                ))
                deltas.append((
                    unit_info.index[new_fighter_id],
                    x / 2,
                    y / 2,
                    "Placed"
                ))
    return deltas
        