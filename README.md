# Sports Arcade

A 2D pygame desktop sports arcade with cricket, football, and badminton modes.

## Play Online

Play the browser version here:

https://garvtanwar.github.io/SportsMania/index.html?v=football-fix-2

Click once on the game area after it loads so the browser gives the game keyboard and mouse focus.

## Gameplay

Open the app and choose Cricket, Football, or Badminton.

Cricket: chase 5 targets to win the trophy. Levels start locked and unlock one at a time as you win. Each level gives you a bigger target and a little more time:

- Level 1: 18 runs in 2 overs
- Level 2: 34 runs in 3 overs
- Level 3: 54 runs in 4 overs
- Level 4: 78 runs in 5 overs
- Level 5: 105 runs in 6 overs

Football: win 5 penalty shootout levels. Choose left, center, or right, then shoot:

- Level 1: 3 goals from 5 penalties
- Level 2: 4 goals from 5 penalties
- Level 3: 4 goals from 6 penalties
- Level 4: 5 goals from 6 penalties
- Level 5: 6 goals from 7 penalties

Badminton: win 5 point-race levels. Choose your return before the shuttle reaches you, then reach the target before the opponent:

- Level 1: first to 5 points
- Level 2: first to 7 points
- Level 3: first to 9 points
- Level 4: first to 11 points
- Level 5: first to 15 points

## Setup

This project supports Python 3.14 by using `pygame-ce`, which installs the same `pygame` import used by the code.

From your existing virtual environment, run:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

## Controls

Sports Menu:

- 1/C: open Cricket
- 2/F: open Football
- 3/B: open Badminton
- Q/Esc: quit the app

Cricket:

- Left Arrow: defensive shot
- Down Arrow: ground shot
- Right Arrow: lofted shot
- Space: power shot
- N/Enter: next level after a successful chase
- R/Enter: retry after a failed chase
- Q/Esc during a match: return to level select
- Q/Esc on level select: return to the sports menu

Football:

- Left Arrow: aim left
- Down/Up Arrow: aim center
- Right Arrow: aim right
- Space: shoot
- N/Enter: next level after a successful shootout
- R/Enter: retry after a failed shootout
- Q/Esc during a shootout: return to level select
- Q/Esc on level select: return to the sports menu

Badminton:

- Left Arrow: prepare a left return
- Down/Up Arrow: prepare a center return
- Right Arrow: prepare a right return
- Space: prepare a smash
- N/Enter: next level after a successful match
- R/Enter: retry after a lost match
- Q/Esc during a match: return to level select
- Q/Esc on level select: return to the sports menu
