"""Stage 1: decide who plays whom (and who's home) before deciding when and where.

Round robin by the circle method, repeated until every team reaches its division's
games-per-team target. Repeats alternate home and away, so a double round robin is
naturally balanced. Splitting "who" from "when" keeps the placement model small and
makes home/away balance exact rather than a trade-off.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from .index import LeagueIndex
from .model import League


@dataclass(frozen=True)
class Matchup:
    id: str
    division_id: str
    home_team_id: str
    away_team_id: str
    round: int  # which round-robin round it came from (used to spread repeats out)

    @property
    def team_ids(self) -> tuple[str, str]:
        return (self.home_team_id, self.away_team_id)


@dataclass(frozen=True)
class MatchupNote:
    division_id: str
    message: str


def circle_rounds(team_ids: list[str]) -> list[list[tuple[str, str]]]:
    """One full round robin. Each round is a list of (home, away) pairs."""
    teams: list[str | None] = list(team_ids)
    if len(teams) % 2:
        teams.append(None)  # bye
    n = len(teams)
    rounds: list[list[tuple[str, str]]] = []
    for r in range(n - 1):
        pairs: list[tuple[str, str]] = []
        for i in range(n // 2):
            a, b = teams[i], teams[n - 1 - i]
            if a is None or b is None:
                continue
            # Alternate the fixed team's home/away each round; others by position.
            home_first = (r % 2 == 0) if i == 0 else (i % 2 == 1)
            pairs.append((a, b) if home_first else (b, a))
        rounds.append(pairs)
        teams = [teams[0], teams[-1], *teams[1:-1]]
    return rounds


def make_matchups(
    league: League, division_ids: list[str] | None = None
) -> tuple[list[Matchup], list[MatchupNote]]:
    ix = LeagueIndex(league)
    teams_by_div: dict[str, list[str]] = defaultdict(list)
    for t in league.teams:
        teams_by_div[t.division_id].append(t.id)
    out: list[Matchup] = []
    notes: list[MatchupNote] = []
    for div in league.divisions:
        if division_ids is not None and div.id not in division_ids:
            continue
        teams = sorted(teams_by_div.get(div.id, []))
        target = ix.division_rules(div.id).games_per_team
        if len(teams) < 2 or target == 0:
            continue
        games, note = _division_games(teams, target)
        if note:
            notes.append(MatchupNote(div.id, f"{div.name}: {note}"))
        for i, (rnd, home, away) in enumerate(games, 1):
            out.append(Matchup(f"g-{div.id}-{i:03d}", div.id, home, away, rnd))
    return out, notes


def _division_games(teams: list[str], target: int) -> tuple[list[tuple[int, str, str]], str]:
    n = len(teams)
    base = circle_rounds(teams)
    games: list[tuple[int, str, str]] = []
    count: Counter[str] = Counter()
    cycle = 0
    while min(count[t] for t in teams) < target:
        for r, pairs in enumerate(base):
            rnd = cycle * len(base) + r
            for home, away in pairs:
                # Every other cycle swaps home and away (double round robin).
                h, a = (home, away) if cycle % 2 == 0 else (away, home)
                games.append((rnd, h, a))
                count[h] += 1
                count[a] += 1
            if min(count[t] for t in teams) >= target:
                break
        cycle += 1

    # Trim from the end until nobody is over target (odd team counts overshoot).
    want = n * target // 2
    for both_over in (True, False):
        i = len(games) - 1
        while len(games) > want and i >= 0:
            _, h, a = games[i]
            over_h, over_a = count[h] > target, count[a] > target
            if (over_h and over_a) if both_over else (over_h or over_a):
                games.pop(i)
                count[h] -= 1
                count[a] -= 1
            i -= 1
    _balance_home_away(games, teams)

    short = sorted(t for t in teams if count[t] < target)
    note = ""
    if short:
        note = (
            f"with {n} teams playing {target} games each, the total can't be split evenly, "
            f"so {len(short)} team{'s' if len(short) > 1 else ''} will play {target - 1}."
        )
    return games, note


def _balance_home_away(games: list[tuple[int, str, str]], teams: list[str]) -> None:
    """Make every team's home and away counts differ by at most one.

    Flipping a chain of games t -> x -> ... -> u (each listed home -> away) moves one
    home game from t to u and leaves everyone in the middle unchanged. Repeat until no
    team has two more home games than away games, or the reverse.
    """
    diff: Counter[str] = Counter({t: 0 for t in teams})
    for _, h, a in games:
        diff[h] += 1
        diff[a] -= 1

    def find_chain(start: str, forward: bool) -> list[int] | None:
        # forward: follow games where the current team is home; stop at a team that
        # can take one more home game (diff <= -1). Backward is the mirror image.
        prev: dict[str, tuple[str, int] | None] = {start: None}
        queue = [start]
        while queue:
            cur = queue.pop(0)
            if cur != start and (diff[cur] <= -1 if forward else diff[cur] >= 1):
                chain: list[int] = []
                node = cur
                while (step := prev[node]) is not None:
                    node, gi = step
                    chain.append(gi)
                return chain
            for gi, (_, h, a) in enumerate(games):
                src, dst = (h, a) if forward else (a, h)
                if src == cur and dst not in prev:
                    prev[dst] = (cur, gi)
                    queue.append(dst)
        return None

    while True:
        worst = max(teams, key=lambda t: abs(diff[t]))
        if abs(diff[worst]) < 2:
            return
        forward = diff[worst] > 0
        chain = find_chain(worst, forward)
        if not chain:
            return  # can't improve (only possible in degenerate cases)
        for gi in chain:
            rnd, h, a = games[gi]
            games[gi] = (rnd, a, h)
            diff[h] -= 2
            diff[a] += 2
