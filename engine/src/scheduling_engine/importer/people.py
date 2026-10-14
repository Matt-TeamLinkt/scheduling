"""Import teams (with optional coach columns) and coaches."""

from __future__ import annotations

from collections import defaultdict

from ..model import Coach, Division, League, Team, Venue
from .columns import Field
from .common import closest, open_sheet
from .plan import (
    Changes,
    Ids,
    ImportKind,
    ImportPreview,
    all_ids,
    check,
    note,
    plural,
    skipped,
    summarize,
)
from .values import key, split_people, tidy_name

TEAM_FIELDS = [
    Field("team", "team name", ("team", "team name", "name", "squad", "team names"), True),
    Field(
        "division",
        "division",
        (
            "division",
            "div",
            "age group",
            "age",
            "level",
            "category",
            "group",
            "age division",
            "league",
        ),
        True,
    ),
    Field(
        "coach",
        "coach",
        (
            "coach",
            "head coach",
            "coaches",
            "coach name",
            "manager",
            "head coach name",
            "coach names",
        ),
    ),
    Field("email", "coach email", ("coach email", "email", "e-mail", "email address")),
    Field("phone", "coach phone", ("coach phone", "phone", "cell", "mobile", "phone number")),
    Field(
        "home",
        "home venue",
        (
            "home venue",
            "home arena",
            "home rink",
            "home field",
            "home park",
            "home facility",
            "home",
        ),
    ),
]

COACH_FIELDS = [
    Field("coach", "coach name", ("coach", "name", "coach name", "head coach", "full name"), True),
    Field("team", "team", ("team", "teams", "team name", "coaches", "team(s)"), True),
    Field("division", "division", ("division", "div", "age group", "level")),
    Field("email", "email", ("email", "e-mail", "email address")),
    Field("phone", "phone", ("phone", "cell", "mobile", "phone number")),
]


class CoachBook:
    """Find-or-create coaches by name, so a coach on several rows becomes one coach."""

    def __init__(self, league: League, ids: Ids, changes: Changes) -> None:
        self.ids, self.changes = ids, changes
        self.by_key: dict[str, Coach] = {key(c.name): c for c in league.coaches}
        self.new_ids: set[str] = set()
        self.teams_of: dict[str, set[str]] = {c.id: set(c.team_ids) for c in league.coaches}

    def get(self, name: str, email: str | None, phone: str | None) -> Coach:
        k = key(name)
        coach = self.by_key.get(k)
        if coach is None:
            coach = Coach(id=self.ids.make("c", name), name=name, email=email, phone=phone)
            self.by_key[k] = coach
            self.new_ids.add(coach.id)
            self.teams_of[coach.id] = set()
            self.changes.coaches.append(coach)
        elif coach.id in self.new_ids:
            coach.email = coach.email or email
            coach.phone = coach.phone or phone
        return coach

    def link(self, coach: Coach, team_id: str) -> bool:
        if team_id in self.teams_of[coach.id]:
            return False
        self.teams_of[coach.id].add(team_id)
        if coach.id in self.new_ids:
            coach.team_ids.append(team_id)
        else:
            self.changes.coach_links.append((coach.id, team_id))
        return True

    def shared(self, team_names: dict[str, str]) -> list[str]:
        """'Alex Ramsey coaches 2 teams (Falcons, Titans)' for every multi-team coach."""
        out = []
        for c in sorted(self.by_key.values(), key=lambda c: c.name):
            teams = sorted(team_names.get(t, t) for t in self.teams_of[c.id])
            if len(teams) > 1:
                out.append(
                    f"{c.name} coaches {len(teams)} teams ({', '.join(teams)}). "
                    "Their games will never be scheduled at the same time."
                )
        return out


def preview_teams(league: League, data: bytes, filename: str) -> ImportPreview:
    sheet = open_sheet(data, filename, TEAM_FIELDS, "teams")
    ch = Changes()
    problems = list(sheet.problems)
    ids = Ids(all_ids(league))
    divisions: dict[str, Division] = {key(d.name): d for d in league.divisions}
    venues: dict[str, Venue] = {key(v.name): v for v in league.venues}
    seen_teams = {(t.division_id, key(t.name)) for t in league.teams}
    coaches = CoachBook(league, ids, ch)
    team_names = {t.id: t.name for t in league.teams}
    existing_div_names = [d.name for d in league.divisions]

    for row in sheet.rows:
        name = sheet.text(row, "team")
        div_name = sheet.text(row, "division")
        if not name:
            if any(c is not None for c in row.cells):
                problems.append(
                    skipped(row.number, f"Row {row.number} has no team name, so it was left out.")
                )
            continue
        name = tidy_name(name)
        if not div_name:
            problems.append(
                skipped(
                    row.number,
                    f"Row {row.number}: {name} has no division, so it was left out. "
                    "Add the division and import again.",
                )
            )
            continue
        div_name = tidy_name(div_name)

        div = divisions.get(key(div_name))
        if div is None:
            div = Division(id=ids.make("d", div_name), name=div_name)
            divisions[key(div_name)] = div
            ch.divisions.append(div)
            near = closest(div_name, existing_div_names)
            if near:
                problems.append(
                    check(
                        row.number,
                        f"Row {row.number}: \"{div_name}\" isn't one of your divisions, so we'll "
                        f"create it. Did you mean {near}? If so, fix the row and import again.",
                    )
                )
            else:
                problems.append(note(row.number, f"We'll create a new division: {div_name}."))

        if (div.id, key(name)) in seen_teams:
            problems.append(
                skipped(
                    row.number,
                    f"Row {row.number}: {div.name} already has a team called {name}, so this "
                    "row was left out.",
                )
            )
            continue
        seen_teams.add((div.id, key(name)))

        home_id = None
        home = sheet.text(row, "home")
        if home:
            v = venues.get(key(home))
            if v is None:
                v = Venue(id=ids.make("v", home), name=tidy_name(home))
                venues[key(home)] = v
                ch.venues.append(v)
                problems.append(
                    note(
                        row.number,
                        f"We'll add {v.name} as a new venue. Add its time slots so games can "
                        "be played there.",
                    )
                )
            home_id = v.id

        team = Team(
            id=ids.make("t", f"{div.name} {name}"),
            name=name,
            division_id=div.id,
            home_venue_id=home_id,
        )
        ch.teams.append(team)
        team_names[team.id] = name

        people = split_people(sheet.text(row, "coach") or "")
        email, phone = sheet.text(row, "email"), sheet.text(row, "phone")
        for i, person in enumerate(people):
            # Contact columns belong to the first coach listed.
            coach = coaches.get(person, email if i == 0 else None, phone if i == 0 else None)
            coaches.link(coach, team.id)

    problems += [note(None, s) for s in coaches.shared(team_names)]
    new_divs = {d.id for d in ch.divisions}
    in_divs = len({t.division_id for t in ch.teams})
    divs = plural(in_divs, "division")
    if new_divs:
        divs += " (all new)" if len(new_divs) == in_divs else f" ({len(new_divs)} of them new)"
    parts = [plural(len(ch.teams), "team") + f" in {divs}"]
    if ch.coaches:
        parts.append(plural(len(ch.coaches), "new coach", "new coaches"))
    summary = summarize(parts, problems, ch)
    return ImportPreview(
        ImportKind.TEAMS, filename, sheet.columns, ch, problems, summary, rows_read=len(sheet.rows)
    )


def preview_coaches(league: League, data: bytes, filename: str) -> ImportPreview:
    """Assign coaches to teams that already exist."""
    sheet = open_sheet(data, filename, COACH_FIELDS, "coaches")
    ch = Changes()
    problems = list(sheet.problems)
    ids = Ids(all_ids(league))
    coaches = CoachBook(league, ids, ch)
    div_by_key = {key(d.name): d.id for d in league.divisions}
    teams_by_key: dict[str, list[Team]] = defaultdict(list)
    for t in league.teams:
        teams_by_key[key(t.name)].append(t)
    team_names = {t.id: t.name for t in league.teams}
    links = 0

    for row in sheet.rows:
        name = sheet.text(row, "coach")
        team_cell = sheet.text(row, "team")
        if not name or not team_cell:
            if any(c is not None for c in row.cells):
                what = "coach name" if not name else "team"
                problems.append(
                    skipped(row.number, f"Row {row.number} has no {what}, so it was left out.")
                )
            continue
        name = tidy_name(name)
        div_cell = sheet.text(row, "division")
        div_id = div_by_key.get(key(div_cell)) if div_cell else None
        # One cell may list several teams: "Falcons; Titans"
        for team_name in [t for t in team_cell.replace("/", ";").split(";") if t.strip()]:
            matches = teams_by_key.get(key(team_name), [])
            if div_id:
                matches = [t for t in matches if t.division_id == div_id]
            if not matches:
                near = closest(team_name, [t.name for t in league.teams])
                hint = f" Did you mean {near}?" if near else ""
                problems.append(
                    skipped(
                        row.number,
                        f'Row {row.number}: there\'s no team called "{team_name.strip()}".{hint} '
                        f"{name} wasn't linked to it.",
                    )
                )
                continue
            if len(matches) > 1:
                problems.append(
                    skipped(
                        row.number,
                        f"Row {row.number}: more than one division has a team called "
                        f"{matches[0].name}. Add a division column so we know which one.",
                    )
                )
                continue
            coach = coaches.get(name, sheet.text(row, "email"), sheet.text(row, "phone"))
            links += coaches.link(coach, matches[0].id)

    problems += [note(None, s) for s in coaches.shared(team_names)]
    parts = [plural(links, "coach assignment")]
    if ch.coaches:
        parts.append(plural(len(ch.coaches), "new coach", "new coaches"))
    summary = summarize(parts, problems, ch)
    return ImportPreview(
        ImportKind.COACHES,
        filename,
        sheet.columns,
        ch,
        problems,
        summary,
        rows_read=len(sheet.rows),
    )
