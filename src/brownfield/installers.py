"""Pass 3g step 8c (D28): the installers' round, its packets and the log of what comes back.

**The packets** (`packet`): one PDF a trade, for Jon to send: a cover letter (from the study, no
name: Jon's own message introduces him), the trade's question form (step 8b) and its sheets from
the latest addendum's set, Addendum 7's (G-001, G-002's tests and the trade's own; the plumber and
the HVAC contractor also get M-602's sequence, and the HVAC contractor and the electrician the
plumbing walls, which their line sets, loop risers and feeders run in). Everything else, the
models, schedules, other sheets and the 3D viewer, is a link to the plan room. No reply-by date.

**The log** (`load_log`, `check_log`): every comment Jon relays goes into a private file on his
machine, `data/raw/round/comments.yaml` (gitignored), with who sent it by trade and county only,
what it's about, their words, whether they agreed to be published (question C6), and what became of
it: open, taken (an addendum item) or answered. Only comments whose author said yes leave that
file (`publish`): each into the public log (`docs/pass3/bidset/round/comments.md`) and as a BCF
topic, as RFIs 001 and 002 were, in the plan room's RFIs folder. The rest are counted, never shown.

**The plan room** gets the round's own folder: the four question forms, the public log, and the
round's state (`round.json`, which the manifest carries).
"""

from __future__ import annotations

import json
import shutil
import textwrap
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np

from . import OUT_DIR, questions

ROOT = OUT_DIR.parent
OUT = OUT_DIR / "pass3" / "round"
INTAKE = ROOT / "data" / "raw" / "round" / "comments.yaml"
BIDSET = ROOT / "docs" / "pass3" / "bidset"
PUBLISHED = BIDSET / "round"
PLAN_ROOM = "https://youngmoolahbaby.github.io/brownfield-compute/"
SHEETS_PDF = "services-sheets-addendum-7.pdf"  # the round's packets carry the latest sheets (Addendum 6's until Addendum 7)
# When the round's question forms were first published to the plan room.
QUESTIONS_ISSUED = "2026-11-22T17:54:51-08:00"
# When they were published again, before any went out, with Addendum 7's figures and sheets and its
# questions (P10, M10, C5; consent moved to C6). Jon: "they haven't gone out, rebuild them please".
QUESTIONS_REISSUED = "2026-11-23T09:04:23-08:00"

TRADES = questions.TRADES
SLUG = {t: questions.TRADES[t].split()[0].lower() for t in TRADES}  # as the forms' files: plumber, hvac, ...
SHEETS = {
    "P": ["G-001", "G-002", "P-101", "P-102", "P-103", "P-201", "P-202", "P-601", "M-602"],
    "M": ["G-001", "G-002", "M-101", "M-102", "M-103", "M-104", "M-601", "M-602", "P-201", "P-202"],
    "E": ["G-001", "G-002", "E-101", "E-102", "E-103", "E-601", "E-602", "P-201", "P-202"],
    "FP": ["G-001", "G-002", "FP-101", "FP-102", "FP-103", "FP-601"],
}
# How the letter names each trade's sheets, and asks for it.
SHEETS_OF = {"P": "plumbing", "M": "heating, cooling and air", "E": "electrical", "FP": "sprinkler"}
A_TRADE = {"P": "a plumber", "M": "an HVAC contractor", "E": "an electrician", "FP": "a sprinkler contractor"}
VIA = ("email", "marked-up PDF", "call", "in person")
STATUS = ("open", "taken", "answered")
FIELDS = ("id", "trade", "county", "received", "via", "about", "comment", "publish", "status")


# ---- The packets ----

def letter_text(trade: str) -> list[str]:
    """The cover letter's paragraphs."""
    return [
        "This is a design study, not a job. A study called brownfield-compute is working out how a data center on a retired "
        "coal plant's site could leave its town better off. Part of that is a 12-flat walk-up near the site whose plumbing, "
        "heating, cooling, ventilation, wiring and sprinklers were designed in full before anyone bids, instead of each trade "
        "designing its own system as part of its bid. The building is made up: there is no owner, no bid date and nothing to win.",
        f"We'd like to know whether the design works for the people who would install it. This packet has the {SHEETS_OF[trade]} "
        f"sheets and a short list of questions for {A_TRADE[trade]}. An hour of your time is plenty, and short answers are fine.",
        "To reply, write on the question form or the sheets and send them back, or talk it through with whoever sent you this.",
        f"Everything else is in the project's plan room: the models (IFC), the schedules, the other trades' sheets, the addenda "
        f"and a 3D viewer. {PLAN_ROOM}",
        "Each comment is logged, and either taken into the design as an addendum or answered. We publish a comment only if you "
        "say yes (the last question), and then by your trade and county only, never your name or your firm's.",
        "Not for construction. Every make and model named is a basis of design, and equals are welcome with their data.",
    ]


def write_letter(trade: str, path: Path, contents: list[str], png: Path | None = None) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    W, H, M = questions.PAGE_W, questions.PAGE_H, questions.MARGIN
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    y = H - M
    ax.text(M, y, "12-flat walk-up: would you look at its " + questions.TITLES[trade].lower() + "?", fontsize=15, weight="bold", va="top")
    y -= 0.55
    for para in letter_text(trade):
        for line in textwrap.wrap(para, 88):
            ax.text(M, y, line, fontsize=10.5, va="top")
            y -= 0.2
        y -= 0.16
    y -= 0.1
    ax.text(M, y, "Thank you,", fontsize=10.5, va="top")
    ax.text(M, y - 0.25, "the brownfield-compute study", fontsize=10.5, va="top", style="italic")
    y -= 0.8
    ax.text(M, y, "In this packet", fontsize=10.5, weight="bold", va="top")
    y -= 0.25
    for c in contents:
        ax.text(M + 0.2, y, "- " + c, fontsize=9.5, va="top")
        y -= 0.19
    ax.text(M, 0.55, "Made up, from the brownfield-compute study: not a real project, nothing is out to bid.", fontsize=7.5, color="#757575")
    path.parent.mkdir(parents=True, exist_ok=True)
    with matplotlib.rc_context({"pdf.fonttype": 42}), PdfPages(
            path, metadata={"Title": f"walk-up installers' round: a letter to the {TRADES[trade]}", "Creator": "brownfield-compute pass 3g step 8c",
                            "CreationDate": None}) as pdf:
        pdf.savefig(fig)
    if png is not None:
        png.mkdir(parents=True, exist_ok=True)
        fig.savefig(png / f"{path.stem}.png", dpi=70, facecolor="white")
    plt.close(fig)


def sheet_pages(pdf_path: Path) -> dict[str, int]:
    """Each sheet's page in the published set, by its number in the title block."""
    import pypdf

    from .servicesheets import sheet_list

    reader = pypdf.PdfReader(str(pdf_path))
    numbers = [n for n, _ in sheet_list()]
    if len(reader.pages) != len(numbers):
        raise ValueError(f"{pdf_path.name} has {len(reader.pages)} pages, the set {len(numbers)}")
    for i, n in enumerate(numbers):  # written in the index's order; each page's own number is on it
        if n not in (reader.pages[i].extract_text() or ""):
            raise ValueError(f"page {i + 1} of {pdf_path.name} isn't {n}")
    return {n: i for i, n in enumerate(numbers)}


def packet(trade: str, form: Path, out: Path, sheets_pdf: Path = BIDSET / SHEETS_PDF) -> dict:
    """One trade's packet: the letter, its question form, its sheets."""
    import pypdf

    from .servicesheets import sheet_list

    titles = dict(sheet_list())
    form_pages = len(pypdf.PdfReader(str(form)).pages)
    contents = ["this letter", f"the questions for the {TRADES[trade]} ({form_pages} pages)"]
    contents += [f"{n}, {titles[n].capitalize()}" for n in SHEETS[trade]]
    from .pdfset import SHEET_H, SHEET_W
    contents.append(f"(the sheets are drawn {SHEET_W:g} x {SHEET_H:g} in.: they read on a screen, or printed at 11 x 17)")
    letter = out / f"letter-{SLUG[trade]}.pdf"
    write_letter(trade, letter, contents, OUT / "png")
    pages = sheet_pages(sheets_pdf)
    w = pypdf.PdfWriter()
    for src in (letter, form):
        w.append(str(src))
    sheets = pypdf.PdfReader(str(sheets_pdf))
    for n in SHEETS[trade]:
        w.add_page(sheets.pages[pages[n]])
    w.add_metadata({"/Title": f"12-flat walk-up: the installers' round, for the {TRADES[trade]}", "/Creator": "brownfield-compute pass 3g step 8c"})
    path = out / f"packet-{SLUG[trade]}.pdf"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as fh:
        w.write(fh)
    return {"path": path, "pages": 1 + form_pages + len(SHEETS[trade]), "sheets": SHEETS[trade]}


# ---- The log ----

def load_log(path: Path = INTAKE) -> list[dict]:
    """The comments as Jon relays them (a YAML list), or none yet."""
    import yaml

    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    if not isinstance(data, list):
        raise ValueError(f"{path}: a list of comments, one entry each")
    return data


def _day(x) -> date | None:
    if isinstance(x, datetime):
        return x.date()
    if isinstance(x, date):
        return x
    try:
        return date.fromisoformat(str(x))
    except ValueError:
        return None


def check_log(entries: list[dict], ids: set[str], sheets: set[str]) -> list[str]:
    """What's wrong with the log, entry by entry: each needs its fields, a trade of the round, a
    known question or sheet it's about, a yes or no to publishing, and, once taken or answered,
    what we said and when."""
    problems = []
    seen = set()
    names = {v: k for k, v in TRADES.items()}
    for i, e in enumerate(entries):
        tag = e.get("id") or f"entry {i + 1}"
        for f in FIELDS:
            if e.get(f) in (None, "", []):
                problems.append(f"{tag}: no {f}")
        if e.get("id") in seen:
            problems.append(f"{tag}: id used twice")
        seen.add(e.get("id"))
        if e.get("trade") not in names:
            problems.append(f"{tag}: trade {e.get('trade')!r} isn't one of the round's ({', '.join(names)})")
        if e.get("via") and e["via"] not in VIA:
            problems.append(f"{tag}: via {e['via']!r} isn't one of {VIA}")
        for ref in e.get("about") or []:
            if ref not in ids and ref not in sheets and ref != "general":
                problems.append(f"{tag}: about {ref!r} is no question, sheet or 'general'")
        if not isinstance(e.get("publish"), bool):
            problems.append(f"{tag}: publish must be yes or no (question C6)")
        if e.get("received") and _day(e["received"]) is None:
            problems.append(f"{tag}: received {e['received']!r} isn't a date")
        status = e.get("status")
        if status not in STATUS:
            problems.append(f"{tag}: status {status!r} isn't one of {STATUS}")
        if status in ("taken", "answered"):
            if not e.get("answer"):
                problems.append(f"{tag}: {status}, so it needs its answer")
            if _day(e.get("answered")) is None:
                problems.append(f"{tag}: {status}, so it needs the date it was answered")
        if status == "taken" and not e.get("addendum"):
            problems.append(f"{tag}: taken, so it needs the addendum that takes it")
    return problems


def summary(entries: list[dict]) -> dict:
    """Counts anyone may see: by trade and status, and how many may be published."""
    by = {t: {s: 0 for s in STATUS} for t in TRADES.values()}
    for e in entries:
        if e.get("trade") in by and e.get("status") in STATUS:
            by[e["trade"]][e["status"]] += 1
    return {"received": len(entries), "public": sum(1 for e in entries if e.get("publish") is True), "by_trade": by}


# ---- Publishing what may be published ----

AUTHOR = {"P": "plumber@example.com", "M": "hvac@example.com", "E": "electrician@example.com", "FP": "sprinkler@example.com"}
ANSWERED_BY = "design@example.com"  # the study's design team, a role, made up as pass 3f's


def write_bcf(e: dict, path: Path, where: dict[str, tuple[str, np.ndarray]]) -> None:
    """A consented comment as a BCF 3.0 topic: their words, by trade and county; a viewpoint on the
    services model's elements it points at, if any; our answer as a comment, the topic closed once
    taken or answered. Repeatable: the zip settled as RFI 002's is."""
    from bcf.v3 import model as mdl
    from bcf.v3.bcfxml import BcfXml
    from xsdata.models.datatype import XmlDateTime

    from .addendum import _settle_zip

    t = {v: k for k, v in TRADES.items()}[e["trade"]]
    ext = mdl.Extensions(topic_types=mdl.ExtensionsTopicTypes(topic_type=["Comment"]),
                         topic_statuses=mdl.ExtensionsTopicStatuses(topic_status=["Open", "Closed"]),
                         users=mdl.ExtensionsUsers(user=sorted({AUTHOR[t], ANSWERED_BY})))
    bcf = BcfXml.create_new("brownfield-compute pass 3g: the installers' round", extensions=ext)
    title = f"{e['id']}: the {e['trade']}, {e['county']}, on {', '.join(e['about'])}"
    topic = bcf.add_topic(title, str(e["comment"]), AUTHOR[t], "Comment", "Open")
    received = XmlDateTime.from_datetime(datetime.combine(_day(e["received"]), datetime.min.time(), tzinfo=timezone.utc))
    topic.topic.creation_date = received
    found = [where[k] for k in e.get("elements") or [] if k in where]
    if found:  # a viewpoint at the middle of what it points at, selecting it
        topic.add_viewpoint_from_point_and_guids(np.mean([pt for _, pt in found], axis=0), *[g for g, _ in found])
    if e["status"] in ("taken", "answered"):
        when = XmlDateTime.from_datetime(datetime.combine(_day(e["answered"]), datetime.min.time(), tzinfo=timezone.utc))
        answer = str(e["answer"]) + (f" (taken in Addendum {e['addendum']})" if e["status"] == "taken" else "")
        topic.comments = (topic.comments or []) + [mdl.Comment(guid=str(uuid.uuid4()), date=when, author=ANSWERED_BY, comment=answer)]
        topic.topic.topic_status = "Closed"
        topic.topic.modified_date, topic.topic.modified_author = when, ANSWERED_BY
    path.parent.mkdir(parents=True, exist_ok=True)
    bcf.save(path)
    _settle_zip(path, e["id"].lower())


def public_log(entries: list[dict], s: dict) -> str:
    """The round's log as the plan room shows it: the counts, then each comment whose author said
    yes. Nothing of the others."""
    lines = ["# The installers' round: what came back", "",
             "Made up, from the brownfield-compute study: not a real project, nothing is out to bid. Each comment is shown "
             "only if its author agreed, and then by trade and county only, with any name of a person or firm taken out.", "",
             f"Comments received: {s['received']}; shown here with their author's OK: {s['public']}.", ""]
    for trade, by in s["by_trade"].items():
        lines.append(f"- {trade}: " + ", ".join(f"{n} {k}" for k, n in by.items()))
    lines.append("")
    for e in entries:
        if e.get("publish") is not True:
            continue
        lines += [f"## {e['id']}: the {e['trade']}, {e['county']} ({_day(e['received']).isoformat()}, by {e['via']})", "",
                  f"About: {', '.join(e['about'])}.", "", *(f"> {line}".rstrip() for line in str(e["comment"]).strip().splitlines()), ""]
        if e["status"] == "open":
            lines += ["Open.", ""]
        else:
            lines += [f"{'Taken in Addendum ' + str(e['addendum']) if e['status'] == 'taken' else 'Answered'} "
                      f"({_day(e['answered']).isoformat()}): {e['answer']}", ""]
    if not s["public"]:
        lines += ["Nothing to show yet.", ""]
    return "\n".join(lines)


def publish(entries: list[dict], forms: dict[str, Path], to: Path = PUBLISHED) -> dict:
    """The question forms, the public log and each consented comment's BCF topic into the plan
    room's round folder, and the round's state (`round.json`) the manifest carries. A comment
    without its author's yes is never written there."""
    from .servicesheets import services

    to.mkdir(parents=True, exist_ok=True)
    for old in to.glob("r-*.bcf"):  # a comment withdrawn, or no longer to be shown, goes
        old.unlink()
    files = []
    for t, src in forms.items():
        dst = to / src.name
        shutil.copyfile(src, dst)
        files.append({"path": f"round/{dst.name}", "label": f"The questions for the {TRADES[t]}"})
    s = summary(entries)
    (to / "comments.md").write_text(public_log(entries, s) + "\n", encoding="utf-8")
    files.append({"path": "round/comments.md", "label": "What came back: the comments shown with their author's OK"})
    shown = [e for e in entries if e.get("publish") is True]
    where = {}  # a services element's GlobalId and where it is, by its key
    if any(e.get("elements") for e in shown):
        from .servicesifc import ISSUE

        for r in services(BIDSET / f"services-{ISSUE}.ifc"):
            pts = np.asarray(r["sweep"] if r["sweep"] is not None else r["box"], float)
            where[r["key"]] = (r["gid"], pts.mean(axis=0))
    rfis = []
    for e in shown:
        path = to / f"{e['id'].lower()}.bcf"
        write_bcf(e, path, where)
        rfis.append({"path": f"round/{path.name}", "label": f"{e['id']}, the {e['trade']} ({e['county']}): {e['status']} (BCF 3.0)",
                     "issued": _day(e["received"]).isoformat() + "T00:00:00-08:00"})
    state = {"issued": QUESTIONS_REISSUED, "first_issued": QUESTIONS_ISSUED, "files": files, "rfis": rfis,
             "note": f"{s['received']} comments received, {s['public']} shown with their author's OK"}
    (to / "round.json").write_text(json.dumps(state, indent=1) + "\n", encoding="utf-8")
    return state


def manifest_entry(bidset: Path = BIDSET) -> dict | None:
    """The round's entry in the plan room's manifest (`addenda.json`), as last published."""
    p = bidset / "round" / "round.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def set_manifest(bidset: Path = BIDSET) -> None:
    """Write the round's entry into the published manifest, keeping the rest of it as it is."""
    path = bidset / "addenda.json"
    m = json.loads(path.read_text(encoding="utf-8"))
    m["round"] = manifest_entry(bidset)
    path.write_text(json.dumps(m, indent=1) + "\n", encoding="utf-8")


# ---- 8c as a run ----

def run(apt: dict, p: dict, publish_to: Path | None = None, intake: Path = INTAKE) -> dict:
    """The question forms (8b), the four packets, the log checked; published if asked and the log
    is sound."""
    from .servicesheets import sheet_list

    q = questions.run(apt, p)
    ids = {x["id"] for t in q["questions"] for x in q["questions"][t]}
    entries = load_log(intake)
    problems = check_log(entries, ids, {n for n, _ in sheet_list()})
    packets = {t: packet(t, q["pdfs"][t], OUT / "packets") for t in TRADES}
    out = {"packets": packets, "entries": entries, "problems": problems, "summary": summary(entries), "intake": intake,
           "published": None}
    if publish_to is not None:
        if problems:
            raise SystemExit("won't publish: the log has problems:\n  " + "\n  ".join(problems))
        out["published"] = publish(entries, q["pdfs"], publish_to)
        set_manifest(publish_to.parent)
    return out


def report(r: dict) -> str:
    s = r["summary"]
    lines = ["Pass 3g step 8c: the installers' round, the packets and the log", ""]
    for t, k in r["packets"].items():
        lines.append(f"Packet for the {TRADES[t]}: {k['path'].name}, {k['pages']} pages (the letter, the questions, "
                     f"{', '.join(k['sheets'])})")
    where = r["intake"].relative_to(ROOT) if r["intake"].is_relative_to(ROOT) else r["intake"]
    lines += ["", f"The log ({where}, private): {s['received']} comments, {s['public']} to be shown with their author's OK"]
    for trade, by in s["by_trade"].items():
        lines.append(f"  {trade}: " + ", ".join(f"{n} {k}" for k, n in by.items()))
    lines += [*(["", "Problems in the log:", *(f"  {x}" for x in r["problems"])] if r["problems"] else [])]
    if r["published"]:
        lines += ["", f"Published to the plan room's round folder: {len(r['published']['files'])} files, "
                      f"{len(r['published']['rfis'])} comments as BCF topics"]
    return "\n".join(lines)

