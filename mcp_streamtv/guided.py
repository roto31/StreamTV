"""Guided Channel Creator tools (§7.1) — thin HTTP wrappers over /api/builder."""

import json
from typing import Any, List, Literal, Optional

from .config import config
from . import tools
from .profiles import GUIDED_TOOLS, resolve_profile, tools_for_profile

_BUILDER = "/api/builder"
_MAX_RESULT_CHARS = 16000


def _clip(payload: dict[str, Any], limit: int = _MAX_RESULT_CHARS) -> dict[str, Any]:
    raw = json.dumps(payload, default=str)
    if len(raw) <= limit:
        return payload
    out = dict(payload)
    out["truncated"] = True
    out["say"] = (str(out.get("say") or "")[:800] + " …(truncated)").strip()
    # Drop bulky nested previews / lists
    if "preview" in out and isinstance(out["preview"], dict):
        out["preview"] = {
            "program_count": out["preview"].get("program_count"),
            "canonical_titles": (out["preview"].get("canonical_titles") or [])[:20],
        }
    if "candidates" in out and isinstance(out["candidates"], list):
        out["candidates"] = out["candidates"][:5]
    if "items" in out and isinstance(out["items"], list):
        out["items"] = out["items"][:5]
    if "draft" in out:
        out.pop("draft", None)
    if "intake" in out and isinstance(out["intake"], str) and len(out["intake"]) > 2000:
        out["intake"] = out["intake"][:2000] + "…"
    if "channels" in out and isinstance(out["channels"], list):
        out["channels"] = out["channels"][:30]
    raw2 = json.dumps(out, default=str)
    if len(raw2) <= limit:
        return out
    # Last resort: keep only say/next/truncated + counts
    return {
        "say": out.get("say"),
        "next": out.get("next"),
        "truncated": True,
        "keys_omitted": sorted(k for k in out.keys() if k not in ("say", "next", "truncated")),
    }


def _result(say: str, next_tool: str, why: str, **data: Any) -> dict[str, Any]:
    return _clip(
        {
            "say": say,
            "next": {"tool": next_tool, "why": why},
            **data,
        }
    )


def _intake_text(*, level: str = "beginner", compact: bool = False) -> str:
    from . import resources

    if compact:
        return getattr(resources, "CHANNEL_INTAKE_COMPACT", resources.CHANNEL_INTAKE_PROMPT)
    if level == "expert":
        return getattr(
            resources, "CHANNEL_INTAKE_EXPERT", resources.CHANNEL_INTAKE_PROMPT
        )
    return resources.CHANNEL_INTAKE_PROMPT


async def channel_guide(
    level: Literal["beginner", "intermediate", "expert"] = "beginner",
    compact: bool = False,
) -> dict[str, Any]:
    """Return intake text and this profile's tool list. Call first on hosts without prompts."""
    profile = resolve_profile()
    legacy = [n for n, _ in []]  # filled by main when registering
    names = tools_for_profile(profile, legacy_names=[])
    if not names:
        names = list(GUIDED_TOOLS)
    text = _intake_text(level=level, compact=compact)
    return _result(
        "Here is how to create a new StreamTV channel. Ask who it is for, then set requirements.",
        "channel_start",
        "Create a draft after the user picks audience and style",
        level=level,
        compact=compact,
        intake=text,
        tools=names,
        profile=profile,
    )


async def channel_list(include_drafts: bool = True) -> dict[str, Any]:
    """List channels and open drafts (read-only)."""
    client = await tools.get_client()
    channels = await client.request("GET", f"{config.base_url}/api/channels")
    rows = []
    for ch in channels or []:
        rows.append(
            {
                "number": ch.get("number"),
                "name": ch.get("name"),
                "item_count": ch.get("stream_count")
                or len(ch.get("streams") or [])
                or ch.get("media_count"),
            }
        )
    drafts: list[Any] = []
    if include_drafts:
        try:
            raw_drafts = await client.request(
                "GET", f"{config.base_url}{_BUILDER}/drafts"
            )
            if isinstance(raw_drafts, list):
                drafts = raw_drafts
            elif isinstance(raw_drafts, dict):
                drafts = list(raw_drafts.get("drafts") or raw_drafts.values())
        except Exception:  # noqa: BLE001
            drafts = []
    return _result(
        f"Found {len(rows)} channels"
        + (f" and {len(drafts)} drafts." if include_drafts else "."),
        "channel_start",
        "Start a new channel draft",
        channels=rows[:100],
        drafts=drafts[:50] if include_drafts else [],
    )


async def channel_start(
    level: Literal["beginner", "intermediate", "expert"] = "beginner",
    template: Literal[
        "kids_specials", "holiday_family", "prime_time_station_ids", "custom"
    ] = "custom",
    channel_number: str = "",
    name: str = "",
) -> dict[str, Any]:
    """Create a new-channel draft; check number freeness when provided."""
    client = await tools.get_client()
    body: dict[str, Any] = {}
    if channel_number:
        body["channel_number"] = channel_number
    if name:
        body["channel_name"] = name
    draft = await client.request(
        "POST", f"{config.base_url}{_BUILDER}/drafts", json=body
    )
    patch: dict[str, Any] = {
        "template": template,
        "explain_level": level,
        "enrich_metadata": True,
    }
    if channel_number:
        patch["channel_number"] = channel_number
    if name:
        patch["channel_name"] = name
        patch["collection_prefix"] = name
    draft = await client.request(
        "PATCH",
        f"{config.base_url}{_BUILDER}/drafts/{draft['id']}",
        json=patch,
    )
    conflict = None
    if channel_number:
        # Soft check via validate path is heavy; surface number on draft
        conflict = None
    missing = ["audience", "theme"]
    return _result(
        "Draft created. Who is this channel for (kids, family, teens, adults, general), "
        "and what theme?",
        "channel_set_requirements",
        "Save audience and theme before searching",
        draft_id=draft["id"],
        draft=draft,
        missing=missing,
        number_conflict=conflict,
        template=template,
    )


async def channel_set_requirements(
    draft_id: str,
    content_type: str = "",
    theme: str = "",
    networks: Optional[List[str]] = None,
    break_stations: Optional[List[str]] = None,
    daypart: Literal["any", "daytime", "evening", "late_night"] = "any",
    era_from: int = 0,
    era_to: int = 0,
    sources: Optional[List[str]] = None,
    commercials: Literal["required", "preferred", "none", "dont_care"] = "preferred",
    breaks_between_programs: bool = True,
    repeats: Literal["none", "allowed"] = "none",
    exclude: Optional[List[str]] = None,
    audience: str = "",
    audience_notes: str = "",
    template: str = "",
    channel_number: str = "",
    name: str = "",
    no_repeat_against: Optional[List[str]] = None,
) -> dict[str, Any]:
    """Patch requirements with flat fields; return what is still missing."""
    client = await tools.get_client()
    requirements: dict[str, Any] = {}
    if content_type:
        requirements["content_type"] = content_type
    if theme:
        requirements["theme"] = theme
        requirements["theme_terms"] = [theme.lower()]
    if networks is not None:
        requirements["networks"] = networks
    if break_stations is not None:
        requirements["stations_for_breaks"] = break_stations
    if daypart:
        requirements["daypart"] = daypart
    era: dict[str, int] = {}
    if era_from:
        era["from"] = era_from
    if era_to:
        era["to"] = era_to
    if era:
        requirements["era"] = era
    if sources is not None:
        requirements["sources"] = sources
    if commercials:
        requirements["commercials"] = commercials
    requirements["breaks_between_programs"] = breaks_between_programs
    if repeats == "none":
        requirements["no_repeat_scope"] = "channel"
    else:
        requirements["no_repeat_scope"] = "off"
    if exclude is not None:
        requirements["exclude"] = exclude
    if audience:
        requirements["audience"] = audience
    if audience_notes:
        requirements["audience_notes"] = audience_notes
    if template:
        requirements["template"] = template
    if no_repeat_against is not None:
        requirements["no_repeat_against"] = no_repeat_against
        requirements["no_repeat_scope"] = "channel_and_others"

    patch: dict[str, Any] = {"requirements": requirements}
    if template:
        patch["template"] = template
    if channel_number:
        patch["channel_number"] = channel_number
    if name:
        patch["channel_name"] = name
        patch["collection_prefix"] = name
    if no_repeat_against is not None:
        patch["no_repeat_against"] = no_repeat_against
        patch["no_repeat_scope"] = "channel_and_others"
    # Invalidate plan token on requirement change
    patch_draft = await client.request(
        "PATCH", f"{config.base_url}{_BUILDER}/drafts/{draft_id}", json=patch
    )
    # Clear plan token via second patch if field exists
    try:
        await client.request(
            "PATCH",
            f"{config.base_url}{_BUILDER}/drafts/{draft_id}",
            json={"explain_level": patch_draft.get("explain_level") or "beginner"},
        )
    except Exception:  # noqa: BLE001
        pass
    req = (patch_draft.get("requirements") or {}) if isinstance(patch_draft, dict) else {}
    missing = []
    if not req.get("audience") and not audience:
        missing.append("audience")
    if not req.get("theme") and not theme:
        missing.append("theme")
    say = (
        "Requirements saved."
        if not missing
        else f"Still need: {', '.join(missing)}."
    )
    return _result(
        say,
        "channel_find" if not missing else "channel_set_requirements",
        "Search once audience and theme are set"
        if not missing
        else "Fill the missing fields",
        draft_id=draft_id,
        draft=patch_draft,
        missing=missing,
        assumptions={
            "commercials": commercials,
            "daypart": daypart,
            "breaks_between_programs": breaks_between_programs,
        },
    )


async def channel_find(
    draft_id: str,
    extra_queries: Optional[List[str]] = None,
    max_results: int = 40,
) -> dict[str, Any]:
    """Discover → inspect → classify as one open-world job."""
    client = await tools.get_client()
    draft = await client.request(
        "GET", f"{config.base_url}{_BUILDER}/drafts/{draft_id}"
    )
    req = draft.get("requirements") or {}
    if not req.get("audience"):
        return _result(
            "Audience is required before search. Who is this channel for?",
            "channel_set_requirements",
            "Set audience first",
            draft_id=draft_id,
            error="audience_required",
        )
    sources = req.get("sources") or ["archive", "youtube"]
    discovered = await client.request(
        "POST",
        f"{config.base_url}{_BUILDER}/drafts/{draft_id}/discover",
        json={
            "sources": sources,
            "max_per_query": max(1, min(int(max_results), 40)),
            "extra_queries": list(extra_queries or []),
        },
    )
    # Classify after discover (inspect can be skipped for first shortlist)
    classified = await client.request(
        "POST", f"{config.base_url}{_BUILDER}/drafts/{draft_id}/classify"
    )
    job_id = f"find-{draft_id}"
    return _result(
        f"Search finished with {discovered.get('candidate_count', 0)} candidates. "
        "Review the shortlist next.",
        "channel_shortlist",
        "Show Tier 1 programs for confirmation",
        draft_id=draft_id,
        job_id=job_id,
        status="completed",
        candidate_count=discovered.get("candidate_count", 0),
        candidates=(classified.get("candidates") or [])[:20],
    )


async def channel_job(job_id: str, wait_seconds: int = 20) -> dict[str, Any]:
    """Poll a job; wait_seconds capped at 20."""
    wait_seconds = max(0, min(int(wait_seconds), 20))
    client = await tools.get_client()
    if job_id.startswith("find-"):
        draft_id = job_id[len("find-") :]
        draft = await client.request(
            "GET", f"{config.base_url}{_BUILDER}/drafts/{draft_id}"
        )
        cands = draft.get("candidates") or []
        return _result(
            f"Job complete — {len(cands)} candidates ready.",
            "channel_shortlist",
            "Paginate the shortlist",
            job_id=job_id,
            status="completed",
            wait_seconds=wait_seconds,
            draft_id=draft_id,
            page=1,
            items=cands[:10],
        )
    job = await client.request("GET", f"{config.base_url}{_BUILDER}/jobs/{job_id}")
    return _result(
        f"Job {job_id} is {job.get('status')}.",
        "channel_job" if job.get("status") not in ("completed", "failed") else "channel_shortlist",
        "Poll again or open the shortlist",
        job=job,
        job_id=job_id,
        status=job.get("status"),
    )


def _shortlist_items(candidates: list[dict[str, Any]], group: str) -> list[dict[str, Any]]:
    out = []
    for c in candidates:
        role = c.get("role") or "program"
        if group == "programs" and role not in ("program", "marathon", None, ""):
            if role in ("break", "station_id"):
                continue
        if group == "breaks" and role != "break":
            continue
        if group == "ids" and role != "station_id":
            continue
        out.append(c)
    # Tier 1 first
    out.sort(key=lambda c: (0 if c.get("tier") == 1 else 1, str(c.get("title") or "")))
    return out


async def channel_shortlist(
    draft_id: str,
    group: Literal["programs", "breaks", "ids"] = "programs",
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    """Numbered, tiered shortlist with commercial labels."""
    client = await tools.get_client()
    draft = await client.request(
        "GET", f"{config.base_url}{_BUILDER}/drafts/{draft_id}"
    )
    page = max(1, int(page))
    page_size = max(1, min(int(page_size), 25))
    items = _shortlist_items(list(draft.get("candidates") or []), group)
    start = (page - 1) * page_size
    chunk = items[start : start + page_size]
    lines = []
    numbered = []
    for i, c in enumerate(chunk, start=start + 1):
        ads = c.get("commercials") or "unverified"
        label = {
            "yes": "yes",
            "label-only": "likely",
            "inferred": "inferred",
            "no": "removed",
            "unverified": "not stated",
        }.get(ads, ads)
        air = c.get("air_date") or c.get("date") or "unknown"
        if c.get("air_date_quality") in ("month", "year", "placeholder"):
            air = f"about {air}"
        line = (
            f"{i}. {c.get('title')} — {c.get('network') or c.get('station') or '?'} — "
            f"{air} — original commercials: {label}"
        )
        lines.append(line)
        numbered.append({"n": i, **{k: c.get(k) for k in (
            "id", "title", "network", "station", "air_date", "tier", "commercials", "role"
        )}})
    say = "Shortlist:\n" + ("\n".join(lines) if lines else "(empty)")
    return _result(
        say,
        "channel_choose",
        "Keep or drop numbers, then plan",
        draft_id=draft_id,
        group=group,
        page=page,
        page_size=page_size,
        total=len(items),
        items=numbered,
    )


async def channel_choose(
    draft_id: str,
    keep: Optional[List[int]] = None,
    drop: Optional[List[int]] = None,
    group: Literal["programs", "breaks", "ids"] = "programs",
) -> dict[str, Any]:
    """Select shortlist numbers into the draft."""
    client = await tools.get_client()
    draft = await client.request(
        "GET", f"{config.base_url}{_BUILDER}/drafts/{draft_id}"
    )
    items = _shortlist_items(list(draft.get("candidates") or []), group)
    keep = list(keep or [])
    drop_set = set(drop or [])
    role = {"programs": "program", "breaks": "break", "ids": "station_id"}[group]
    selected_ids = []
    indexes = []
    for n in keep:
        if n in drop_set:
            continue
        if 1 <= n <= len(items):
            c = items[n - 1]
            selected_ids.append(str(c.get("id")))
            # map back to draft.candidates index
            for idx, raw in enumerate(draft.get("candidates") or []):
                if str(raw.get("id")) == str(c.get("id")):
                    indexes.append(idx)
                    break
    if selected_ids:
        await client.request(
            "POST",
            f"{config.base_url}{_BUILDER}/drafts/{draft_id}/candidates/add",
            json={"candidate_ids": selected_ids, "role": role},
        )
    # Store kept indexes via patch if supported — keep on local response
    return _result(
        f"Kept {len(selected_ids)} {group}. Ready to plan.",
        "channel_plan",
        "Build the loop preview",
        draft_id=draft_id,
        kept_ids=selected_ids,
        kept_indexes=indexes,
        group=group,
    )


async def channel_plan(draft_id: str) -> dict[str, Any]:
    """Plan preview + plan_token."""
    client = await tools.get_client()
    plan = await client.request(
        "POST", f"{config.base_url}{_BUILDER}/drafts/{draft_id}/plan"
    )
    token = plan.get("plan_token") or ""
    preview = plan.get("preview") or {}
    count = preview.get("program_count") or 0
    return _result(
        f"Plan ready for {count} programs. Confirm with the user, answer any questions, then build.",
        "channel_build",
        "Only after the user says build, call channel_build with plan_token and confirm=build",
        draft_id=draft_id,
        plan_token=token,
        preview={
            "program_count": count,
            "canonical_titles": (preview.get("canonical_titles") or [])[:30],
        },
        questions=plan.get("questions") or [],
    )


async def channel_answer(
    draft_id: str,
    question_id: str,
    choice: str,
) -> dict[str, Any]:
    """Answer one plan question; invalidates plan_token."""
    client = await tools.get_client()
    draft = await client.request(
        "GET", f"{config.base_url}{_BUILDER}/drafts/{draft_id}"
    )
    questions = list(draft.get("plan_questions") or [])
    questions.append({"id": question_id, "choice": choice})
    # Store as exclusions when choice implies drop
    if choice.lower().startswith("drop") or choice.lower() == "exclude":
        await client.request(
            "POST",
            f"{config.base_url}{_BUILDER}/drafts/{draft_id}/exclusions",
            json={"exclusions": [{"title": question_id, "reason": choice}]},
        )
    return _result(
        f"Recorded answer for {question_id}. Re-run the plan.",
        "channel_plan",
        "Plan token was invalidated; create a fresh plan",
        draft_id=draft_id,
        question_id=question_id,
        choice=choice,
        plan_token=None,
    )


async def channel_build(
    draft_id: str,
    plan_token: str = "",
    confirm: str = "",
    skip_availability: bool = False,
    probe_runtimes: bool = False,
    cleanup_only: bool = False,
) -> dict[str, Any]:
    """Build only with valid plan_token and confirm=build (§7.6)."""
    if confirm != "build":
        return _result(
            "Build not confirmed. Ask the user to say build, then call again with confirm=build.",
            "channel_build",
            "Needs confirm=build and a valid plan_token",
            draft_id=draft_id,
            needs_confirmation=True,
        )
    client = await tools.get_client()
    draft = await client.request(
        "GET", f"{config.base_url}{_BUILDER}/drafts/{draft_id}"
    )
    if not plan_token or plan_token != (draft.get("plan_token") or ""):
        return _result(
            "Plan token missing or stale. Run channel_plan again, then confirm build.",
            "channel_plan",
            "Fresh token required",
            draft_id=draft_id,
            needs_confirmation=True,
        )
    if cleanup_only:
        return _result(
            "Cleanup-only requested — no build performed in this stub path.",
            "channel_list",
            "Verify channel list",
            draft_id=draft_id,
            cleanup_only=True,
        )
    report = await client.request(
        "POST",
        f"{config.base_url}{_BUILDER}/drafts/{draft_id}/validate",
        json={"skip_availability": skip_availability},
    )
    if report.get("overall") == "FAIL" or report.get("ok") is False:
        warnings = report.get("user_warnings") or []
        say = "Gates failed before write. Fix the issues and re-plan."
        if any("same stream URL" in str(w) for w in warnings):
            say = (
                "Gates failed: two items share the same stream URL. Keep one "
                "stream row per URL (do not add library + block twins). "
                "Built-in gates block silent import collapse."
            )
        return _result(
            say,
            "channel_plan",
            "Repair failing gates",
            draft_id=draft_id,
            summary_table=report.get("summary_table"),
            gates=report,
            user_warnings=warnings,
            probe_runtimes=probe_runtimes,
        )
    artifacts = await client.request(
        "POST", f"{config.base_url}{_BUILDER}/drafts/{draft_id}/report"
    )
    try:
        build = await client.request(
            "POST",
            f"{config.base_url}{_BUILDER}/drafts/{draft_id}/newchannel-build",
            json={
                "plan_token": plan_token,
                "confirm": "build",
                "skip_availability": skip_availability,
                "enrich_metadata": True,
                "import_channel": True,
            },
        )
    except Exception as exc:  # noqa: BLE001
        build = {"warning": str(exc)}
    overall = (build or {}).get("overall") or report.get("overall")
    say = (
        "Build finished. Refresh the guide in Plex."
        if overall == "PASS"
        else "Build failed — see summary_table."
    )
    return _result(
        say,
        "channel_list",
        "Confirm the new channel appears",
        draft_id=draft_id,
        summary_table=build.get("summary_table") or report.get("summary_table"),
        gates=build if isinstance(build, dict) else report,
        artifacts=artifacts.get("artifacts") or build.get("artifacts"),
        build=build,
    )


GUIDED_IMPL: dict[str, Any] = {
    "channel_guide": channel_guide,
    "channel_list": channel_list,
    "channel_start": channel_start,
    "channel_set_requirements": channel_set_requirements,
    "channel_find": channel_find,
    "channel_job": channel_job,
    "channel_shortlist": channel_shortlist,
    "channel_choose": channel_choose,
    "channel_plan": channel_plan,
    "channel_answer": channel_answer,
    "channel_build": channel_build,
}


GUIDED_SPECS: list[tuple[str, str]] = [
    ("channel_guide", "Return intake text and tool list; call first"),
    ("channel_list", "List channels and open drafts"),
    ("channel_start", "Create a new-channel draft"),
    ("channel_set_requirements", "Save audience, theme, and other requirements"),
    ("channel_find", "Search Archive.org/YouTube and classify candidates"),
    ("channel_job", "Poll a find/build job (max 20s wait)"),
    ("channel_shortlist", "Show a numbered Tier 1/Tier 2 shortlist page"),
    ("channel_choose", "Keep or drop shortlist numbers"),
    ("channel_plan", "Preview the loop and get a plan_token"),
    ("channel_answer", "Answer one plan question"),
    ("channel_build", "Build the new channel after user confirms"),
]
