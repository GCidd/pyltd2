# pyltd2

Client package for the download of Legion TD 2 game data. 

# Installation

## Dependencies

* numpy (>= 1.16.5)
* pandas (>= 1.2.0)
* tqdm (>= 4.64.0)
* requests (>= 2.1.0)

--- 

`pyltdq2` can be installed using pip with the following command:
```
pip install pyltd2
```

# Data structure
The object stores the data into five separate objects, regarding separate information about each match:
1. <details><summary>The fighters the player built during each wave and their position</summary>(_id, playerId, wave, fighter, x, y, seq_num)</details>
2. <details><summary>The actions (Placed/Sold/Upgraded) the player made during each wave (alternative to the previous one, makes the file smaller but requires re-building the data)</summary>(_id, playerId, wave, fighter, x, y, action, seq_num)</details>
3. <details><summary>The fighters the player had</summary>(_id, playerId, fighter_1, fighter_2, ..., fighter_30)</details>
4. <details><summary>The king's hp at the end of the wave</summary>(_id, wave, left_hp, right_hp)</details>
5. <details><summary>The king's upgrades bought by each player during each wave</summary>(_id, playerId, wave, upgrade, seq_num)</details>
6. <details><summary>The leaks a player had during each wave</summary>(_id, playerId, wave, unit, seq_num)</details>
7. <details><summary>The match itself</summary>(_id, version, date, queueType, endingWave, gameLength, gameElo, playerCount, humanCount, kingSpell, side_won)</details>
8. <details><summary>The mercenaries the player received or sent during a wave</summary>(_id, playerId, received, wave, mercenary, seq_num)</details>
9. <details><summary>The party members of each match</summary>(_id, member_1, member_2, member_3, member_4, member_5, member_6, member_7, member_8)</details>
10. <details><summary>The players of the match</summary>(_id, playerId, playerName, playerSlot, legion, workers, value, cross, overallElo, stayedUntilEnd, chosenSpell, partySize, legionSpecificElo, mvpScore, leekValue, leaksCaughtValue, leftAtSeconds)</details>
11. <details><summary>The player's economy during each wave</summary>(_id, playerId, wave, workers, income, networth)</details>
12. <details><summary>The spell upgrades available in the match</summary>(_id, choice_1, choice_2, choice_3)</details>

# Examples
The following example shows how to get the details of the next 50 matches, starting from the first match played (2018-08-03T15:39:00Z) and returning the data as a DataFrame object.
```
from pyltd2 import LTD2Fetcher

fetcher = LTD2Fetcher("your_api_token")
fetcher.get(return_as_df=True)
```
The object uses the [getMatchesByFilter](https://swagger.legiontd2.com/#/Games/getMatchesByFilter) API command to fetch a maximum of 50 matches, starting from the date_after datetime provided.

To download data for the period of time between date_after-date_before and save them to a csv file, you can use the ExhaustiveFetcher object.
The following example downloads matches from 2018-08-03T15:39:00Z until 2019-12-25T22:03:40Z and saves the data to csv files inside the data folder.
```
from datetime import datetime
from pyltd2 import LTD2Fetcher, ExhaustiveFetcher

fetcher = LTD2Fetcher(
    "your_api_token", 
    date_after=datetime(2018, 8, 3, 15, 39, 00), 
    date_before=datetime(2019, 12, 25, 22, 3, 40)
)
api2csv = ExhaustiveFetcher("./data", fetcher=fetcher)
api2csv.start_fetching()
```

You can get your own api token by registering [here](https://developer.legiontd2.com/home).
