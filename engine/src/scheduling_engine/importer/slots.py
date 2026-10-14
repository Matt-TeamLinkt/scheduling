"""Import facility time slots (the ice/field schedule a venue sends the league)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from ..index import fmt_minutes, fmt_time
from ..model import League, Slot, Surface, Venue
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
from .values import (
    date_order_hint,
    key,
    parse_date,
    parse_minutes,
    parse_money,
    parse_time,
    parse_time_range,
    text,
    tidy_name,
)

SLOT_FIELDS = [
    Field(
        "venue",
        "venue",
        (
            "venue",
            "facility",
            "location",
            "arena",
            "park",
            "complex",
            "site",
            "facility name",
            "venue name",
            "arena name",
        ),
        True,
    ),
    Field(
        "surface",
        "rink or field",
        (
            "surface",
            "rink",
            "field",
            "diamond",
            "court",
            "pad",
            "sheet",
            "ice surface",
            "field name",
            "rink name",
        ),
    ),
    Field("date", "date", ("date", "day", "game date", "start date", "ice date"), True),
    Field("start", "start time", ("start", "start time", "from", "begins", "time in")),
    Field("end", "end time", ("end", "end time", "to", "until", "finish", "time out")),
    Field("time", "time", ("time", "times", "ice time", "slot", "time slot", "hours")),
    Field("length", "length", ("length", "duration", "minutes", "mins", "slot length")),
    Field("cost", "cost", ("cost", "price", "rate", "fee", "amount")),
]


def preview_slots(league: League, data: bytes, filename: str) -> ImportPreview:
    sheet = open_sheet(data, filename, SLOT_FIELDS, "time slots")
    ch = Changes()
    problems = list(sheet.problems)
    ids = Ids(all_ids(league))
    preset = league.preset

    if sheet.rows and not (sheet.has("start") or sheet.has("time")):
        problems.append(
            skipped(
                None,
                'We couldn\'t find a start time column. Add a column headed "Start" '
                '(and "End" or "Length"), or one headed "Time" like 7:00 PM - 8:15 PM.',
            )
        )
        sheet.rows = []

    date_strings = [d for r in sheet.rows if (d := text(sheet.get(r, "date")))]
    day_first, ambiguous = date_order_hint(date_strings)
    if ambiguous:
        problems.append(
            check(
                None,
                "Some dates could be read either way (like 03/04). We read them as "
                "month/day. If that's wrong, write dates as 2027-04-03 and import again.",
            )
        )

    venues: dict[str, Venue] = {key(v.name): v for v in league.venues}
    surfaces_at: dict[str, list[Surface]] = {}
    for surf in league.surfaces:
        surfaces_at.setdefault(surf.venue_id, []).append(surf)
    existing = {(sl.surface_id, sl.date, sl.start, sl.end) for sl in league.slots}
    venue_names = [v.name for v in league.venues]
    surface_label = preset.surface_label

    for row in sheet.rows:
        n = row.number
        venue_name = sheet.text(row, "venue")
        if not venue_name:
            if any(c is not None for c in row.cells):
                problems.append(skipped(n, f"Row {n} has no venue, so it was left out."))
            continue

        day = parse_date(sheet.get(row, "date"), day_first)
        if day is None:
            raw = sheet.text(row, "date")
            what = f'"{raw}" isn\'t a date we recognize' if raw else "there's no date"
            problems.append(
                skipped(n, f"Row {n}: {what}, so it was left out. Try a format like 2027-01-09.")
            )
            continue

        times = _times(
            sheet.get(row, "start"),
            sheet.get(row, "end"),
            sheet.get(row, "length"),
            sheet.get(row, "time"),
        )
        if isinstance(times, str):
            problems.append(skipped(n, f"Row {n}: {times}, so it was left out."))
            continue
        start, end = times

        # Venue and surface
        venue = venues.get(key(venue_name))
        if venue is None:
            venue = Venue(id=ids.make("v", venue_name), name=tidy_name(venue_name))
            venues[key(venue_name)] = venue
            ch.venues.append(venue)
            near = closest(venue_name, venue_names)
            if near:
                problems.append(
                    check(
                        n,
                        f"Row {n}: \"{venue.name}\" isn't one of your venues, so we'll add it. "
                        f"Did you mean {near}? If so, fix the row and import again.",
                    )
                )
            else:
                problems.append(note(n, f"We'll add a new venue: {venue.name}."))
        here = surfaces_at.setdefault(venue.id, [])
        surface_name = sheet.text(row, "surface")
        surface: Surface | None
        if surface_name:
            surface = next((s for s in here if key(s.name) == key(surface_name)), None)
            if surface is None:
                surface = _new_surface(ids, venue, tidy_name(surface_name), preset.full_units)
                here.append(surface)
                ch.surfaces.append(surface)
        elif len(here) == 1:
            surface = here[0]
        elif not here:
            surface = _new_surface(ids, venue, surface_label.title(), preset.full_units)
            here.append(surface)
            ch.surfaces.append(surface)
        else:
            problems.append(
                skipped(
                    n,
                    f"Row {n}: {venue.name} has {len(here)} {surface_label}s, so we don't know "
                    f'which one this is. Add a "{surface_label.title()}" column.',
                )
            )
            continue

        slot_key = (surface.id, day, start, end)
        if slot_key in existing:
            problems.append(
                skipped(
                    n,
                    f"Row {n}: {_where(venue, surface)} already has {fmt_time(_dt(day, start))}–"
                    f"{fmt_time(_dt(day, end))} on {day:%b} {day.day}, so it was left out.",
                )
            )
            continue
        existing.add(slot_key)

        if not league.season_start <= day <= league.season_end:
            problems.append(
                check(
                    n,
                    f"Row {n}: {day:%b} {day.day}, {day.year} is outside your season, so this "
                    "slot won't be used unless you change the season dates.",
                )
            )

        cost_cell = sheet.get(row, "cost")
        cost = parse_money(cost_cell)
        if cost_cell is not None and cost is None:
            problems.append(
                check(
                    n,
                    f'Row {n}: we couldn\'t read the cost "{text(cost_cell)}", so it was left '
                    "blank.",
                )
            )
        ch.slots.append(
            Slot(
                id=ids.make("sl", f"{surface.id}-{day}-{start:%H%M}"),
                surface_id=surface.id,
                date=day,
                start=start,
                end=end,
                cost=cost,
            )
        )

    total = fmt_minutes(sum(s.minutes for s in ch.slots))
    parts = [plural(len(ch.slots), "time slot") + f" ({total})"]
    if ch.venues:
        parts.append(plural(len(ch.venues), "new venue"))
    if ch.surfaces:
        parts.append(plural(len(ch.surfaces), f"new {surface_label}"))
    summary = summarize(parts, problems, ch)
    return ImportPreview(
        ImportKind.SLOTS, filename, sheet.columns, ch, problems, summary, rows_read=len(sheet.rows)
    )


def _times(
    start_c: object, end_c: object, length_c: object, range_c: object
) -> tuple[time, time] | str:
    """Work out start and end from whichever columns the file has, or say what's wrong."""
    start = parse_time(start_c)  # type: ignore[arg-type]
    end = parse_time(end_c)  # type: ignore[arg-type]
    if start is None and range_c is not None:
        rng = parse_time_range(range_c)  # type: ignore[arg-type]
        if rng:
            start, end = rng
        else:
            start = parse_time(range_c)  # type: ignore[arg-type]
    if start is None:
        raw = text(start_c or range_c)  # type: ignore[arg-type]
        return f'"{raw}" isn\'t a time we recognize' if raw else "there's no start time"
    if end is None:
        minutes = parse_minutes(length_c)  # type: ignore[arg-type]
        if minutes is None:
            return "there's no end time or length"
        finish = datetime.combine(date.min, start) + timedelta(minutes=minutes)
        if finish.date() != date.min:
            return "the slot runs past midnight"
        end = finish.time()
    if end <= start:
        return (
            f"it ends ({fmt_time(_dt(date.min, end))}) before it starts "
            f"({fmt_time(_dt(date.min, start))})"
        )
    return start, end


def _new_surface(ids: Ids, venue: Venue, name: str, units: int) -> Surface:
    return Surface(
        id=ids.make("s", f"{venue.name} {name}"), venue_id=venue.id, name=name, units=units
    )


def _where(venue: Venue, surface: Surface) -> str:
    return venue.name if surface.name == venue.name else f"{venue.name} {surface.name}"


def _dt(d: date, t: time) -> datetime:
    return datetime.combine(d, t)
