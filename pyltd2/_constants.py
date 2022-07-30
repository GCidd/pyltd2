from datetime import datetime
FIRST_MATCH_DATE = datetime(2018, 8, 3, 15, 39, 00)

SORTBY_DATE = "date"
SORTBY_ELO = "gameElo"
SORTBY_WAVE = "wave"
SORTBY_QTYPE = "queueType"
SORTBY_LENGTH = "gameLength"

SORT_ASCEND = 1
SORT_DESCEND = -1

QTYPE_NORM = "Normal"
QTYPE_CLASSIC = "Classic"
QTYPE_ARCADE = "Arcade"

MAX_OFFSET = 50_000

MATCH = {
    "_id": [],
    "version": [],
    "date": [],
    "queueType": [],
    "endingWave": [],
    "gameLength": [],
    "gameElo": [],
    "playerCount": [],
    "humanCount": [],
    "kingSpell": [],
    "side_won": []
}
PLAYER = {
    "_id": [],
    "playerId": [],
    "playerName": [],
    "playerSlot": [],
    "legion": [],
    "workers": [],
    "value": [],
    "cross": [],
    "overallElo": [],
    "stayedUntilEnd": [],
    "chosenSpell": [],
    "partySize": [],
    "legionSpecificElo": [],
    "mvpScore": [],
    "leakValue": [],
    "leaksCaughtValue": [],
    "leftAtSeconds": [],
}
PARTY = {
    "_id": [],
    "member_1": [],
    "member_2": [],
    "member_3": [],
    "member_4": [],
    "member_5": [],
    "member_6": [],
    "member_7": [],
    "member_8": [],
}
# TODO: Fix number of data for FIGHTERS and ROLLS
FIGHTERS = {
    "_id": [],
    "playerId": [],
}
for i in range(30):
    FIGHTERS[f"fighter_{i+1}"] = []
ROLLS = {
    "_id": [],
    "playerId": [],
}
for i in range(30):
    ROLLS[f"roll_{i+1}"] = []
SPELLS = {
    "_id": [],
    "choice_1": [],
    "choice_2": [],
    "choice_3": [],
}
KINGS_HPS = {
    "_id": [],
    "wave": [],
    "left_hp": [],
    "right_hp": []
}
KINGS_UPGRADES = {
    "_id": [],
    "playerId": [],
    "wave": [],
    "upgrade": [],
    "seq_num": []
}
PLAYER_WAVES = {
    "_id": [],
    "playerId": [],
    "wave": [],
    "workers": [],
    "income": [],
    "networth": []
}
MERCENARIES = {
    "_id": [],
    "playerId": [],
    "received": [],
    "wave": [],
    "mercenary": [],
    "seq_num": []
}
LEAKS = {
    "_id": [],
    "playerId": [],
    "wave": [],
    "unit": [],
    "seq_num": []
}
BUILDS = {
    "_id": [],
    "playerId": [],
    "wave": [],
    "fighter": [],
    "x": [],
    "y": [],
    "stacks": [],
    "seq_num": []
}
DELTA_BUILDS = {
    "_id": [],
    "playerId": [],
    "wave": [],
    "fighter": [],
    "x": [],
    "y": [],
    "stacks": [],
    "seq_num": [],
    "action": []
}

UNIT_INFO_URL = "https://github.com/GCidd/pyltd2/blob/main/constants/fighters_v9.04.csv"
UNIT_UPGRADES_TREE_URL = "https://github.com/GCidd/pyltd2/blob/main/constants/upgrades_tree.json"