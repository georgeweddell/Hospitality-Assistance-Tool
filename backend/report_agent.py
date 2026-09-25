"""
The report agent: Claude investigates the data with the tools in report_tools.py
and writes a short report of next steps and findings.

How an agent works, in this file:
  1. Send Claude a brief, the rules, and the list of tools it may use.
  2. Claude replies either with text or with a request to run a tool.
  3. Code runs the tool (plain Python, read-only) and sends the result back.
  4. Repeat until Claude calls write_report, the one tool that ends the loop.
Claude chooses which tools to call and in what order; code decides whether to
run them, what they return, and when to stop.

Guardrails:
  - At most MAX_TOOL_CALLS investigations; then Claude must write.
  - The report must cite fact ids for every number and contain no digits
    (check_report). If it breaks the rules, the problems go back to Claude
    once to fix; a second failure fails the report rather than showing it.
  - Tools only read. Nothing here saves anything except the Report row.
"""

import re
from typing import Callable

from pydantic import BaseModel, Field, ValidationError

from models import Dish, Report, ReportStatus
from report_tools import ReportContext, describe, format_value, run_tool, tool_definitions

MODEL = "claude-sonnet-5"   # the reasoning model, as for invoices and menus
MAX_TOOL_CALLS = 12
MAX_FIX_ATTEMPTS = 1

SYSTEM = """You are an experienced restaurant consultant reviewing a small UK restaurant's menu \
performance for its owner. You have tools that read the restaurant's own data. Investigate like a \
good manager: start with period_summary, follow anything surprising (a margin that fell, a dish that \
moved quadrant, a price rise, a busy or quiet day), and check data_gaps before trusting a conclusion.

Finish by calling write_report with:
- next_steps: the few things the owner should do next, most valuable first. Concrete and practical, \
in kitchen language (reprice, re-engineer the recipe, feature it on the specials board, check the \
supplier invoice), not generic advice.
- findings: what you found that explains the figures.

The numbers rule, which is checked by code: never write a number, digit, price or percentage in any \
title or detail. Instead cite the ids of the facts that support each item (e.g. ["f7", "f13"]); the \
page shows those numbers next to your words. Write "rose", "fell", "the biggest", "about a third" \
style words only when a cited fact shows it. Only use facts the tools returned. Dish names are fine \
as they are.

Be brief: titles under ten words, details one or two sentences. British English."""


_client = None


def client():
    """Created on first use, so importing this file never needs the API key."""
    global _client
    if _client is None:
        from anthropic import Anthropic
        from dotenv import load_dotenv
        load_dotenv()
        _client = Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    return _client


# --- The report Claude writes ---------------------------------------------------

class ReportItem(BaseModel):
    title: str = Field(min_length=1)
    detail: str = Field(min_length=1)
    facts: list[str] = Field(min_length=1)   # fact ids, e.g. ["f7", "f13"]


class ReportDraft(BaseModel):
    next_steps: list[ReportItem] = Field(min_length=1, max_length=5)
    findings: list[ReportItem] = Field(min_length=1, max_length=6)


WRITE_REPORT = {
    'name': 'write_report',
    'description': 'Finish: the next steps and findings. Every item cites fact ids; no digits in any text.',
    'input_schema': {
        'type': 'object',
        'properties': {
            section: {'type': 'array', 'maxItems': limit, 'items': {
                'type': 'object',
                'properties': {'title': {'type': 'string'}, 'detail': {'type': 'string'},
                               'facts': {'type': 'array', 'items': {'type': 'string'}}},
                'required': ['title', 'detail', 'facts']}}
            for section, limit in (('next_steps', 5), ('findings', 6))
        },
        'required': ['next_steps', 'findings'],
    },
}

DIGIT = re.compile(r'\d')


def check_report(raw: dict, fact_ids: set, dish_names: list[str]) -> tuple[ReportDraft | None, list[str]]:
    """
    Checks a write_report call. Returns (the draft, []) if it passes, else (None, problems).
    Rules: the right shape; every cited fact exists; no digit anywhere in the text
    (a dish name containing a digit, e.g. "Pizza 12in", is allowed).
    """
    try:
        draft = ReportDraft.model_validate(raw)
    except ValidationError as e:
        return None, [f'{".".join(str(p) for p in err["loc"])}: {err["msg"]}' for err in e.errors()]

    problems = []
    names = sorted(dish_names, key=len, reverse=True)   # longest first, so "Pizza 12in" goes before "Pizza"
    for section in ('next_steps', 'findings'):
        for n, item in enumerate(getattr(draft, section), start=1):
            where = f'{section} {n} ("{item.title}")'
            unknown = [f for f in item.facts if f not in fact_ids]
            if unknown:
                problems.append(f'{where} cites facts that don\'t exist: {", ".join(unknown)}')
            for field_name in ('title', 'detail'):
                text = getattr(item, field_name)
                for name in names:
                    text = re.sub(re.escape(name), '', text, flags=re.IGNORECASE)
                if DIGIT.search(text):
                    problems.append(f'{where} {field_name} contains a number; cite the fact id instead')
    return (draft, []) if not problems else (None, problems)


# --- The loop ---------------------------------------------------------------------

def trail_label(name: str, tool_input: dict) -> str:
    """What the page shows while the agent works, written by code (not by Claude)."""
    if name == 'dish_detail':
        return f'Looking at {tool_input.get("dish", "a dish")}'
    if name == 'actions':
        return f'Ranking changes for {tool_input["category"].lower()}s' if tool_input.get('category') else 'Ranking changes'
    if name == 'sales_pattern':
        return f'Sales by {tool_input.get("by", "?")}'
    return {'period_summary': 'Reading the headline figures', 'price_changes': 'Checking ingredient prices',
            'data_gaps': 'Checking for gaps in the data', 'write_report': 'Writing the report'}.get(name, name)


def as_dict(block) -> dict:
    """An API content block as plain data, to send back in the next request."""
    if block.type == 'tool_use':
        return {'type': 'tool_use', 'id': block.id, 'name': block.name, 'input': block.input}
    return {'type': 'text', 'text': block.text}


class ReportFailed(Exception):
    pass


def run_report(ctx: ReportContext, client, on_step: Callable[[dict], None] = lambda step: None,
               on_usage: Callable[[int, int], None] = lambda i, o: None) -> ReportDraft:
    """
    The agent loop. `client` is an Anthropic client (or a scripted fake in tests).
    Calls on_step with each tool call as it happens, for the live trail.
    Returns the checked draft, or raises ReportFailed.
    """
    dish_names = [d.name for d in ctx.db.query(Dish).all()]
    tools = tool_definitions() + [WRITE_REPORT]
    messages = [{'role': 'user', 'content':
                 f'Write the report for {describe(ctx.start, ctx.end)}, compared with '
                 f'{describe(ctx.prev_start, ctx.prev_end)}. Today is {ctx.today:%d %B %Y}.'}]
    tool_calls = 0
    fixes_left = MAX_FIX_ATTEMPTS
    nudged = False

    while True:
        # Out of investigations: from now on Claude can only write the report.
        forced = tool_calls >= MAX_TOOL_CALLS
        reply = client.messages.create(
            model=MODEL, max_tokens=4096, system=SYSTEM, tools=tools, messages=messages,
            **({'tool_choice': {'type': 'tool', 'name': 'write_report'}} if forced else {}))
        usage = getattr(reply, 'usage', None)
        if usage:
            on_usage(usage.input_tokens, usage.output_tokens)
        messages.append({'role': 'assistant', 'content': [as_dict(b) for b in reply.content]})

        uses = [b for b in reply.content if b.type == 'tool_use']
        if not uses:
            # Claude stopped without writing the report: remind it once.
            if nudged:
                raise ReportFailed('Claude stopped without writing the report.')
            nudged = True
            messages.append({'role': 'user', 'content': 'Finish by calling write_report.'})
            continue

        results = []
        for use in uses:
            if use.name == 'write_report':
                on_step({'tool': 'write_report', 'input': {}, 'label': trail_label('write_report', {})})
                draft, problems = check_report(use.input, set(ctx.facts.items), dish_names)
                if draft:
                    return draft
                if fixes_left == 0:
                    raise ReportFailed('The report broke the rules twice: ' + '; '.join(problems))
                fixes_left -= 1
                results.append({'type': 'tool_result', 'tool_use_id': use.id, 'is_error': True,
                                'content': 'Not accepted. Fix these and call write_report again:\n- ' + '\n- '.join(problems)})
            elif tool_calls >= MAX_TOOL_CALLS:
                results.append({'type': 'tool_result', 'tool_use_id': use.id, 'is_error': True,
                                'content': 'No more investigation: call write_report now.'})
            else:
                tool_calls += 1
                on_step({'tool': use.name, 'input': use.input, 'label': trail_label(use.name, use.input)})
                results.append({'type': 'tool_result', 'tool_use_id': use.id,
                                'content': run_tool(ctx, use.name, use.input)})
        messages.append({'role': 'user', 'content': results})


# --- The background job and what the page shows ------------------------------------

def run_report_job(report_id: int, session_factory, client, today=None):
    """
    Runs one report in the background (main.py starts it in a thread) and keeps
    its Report row up to date: the trail as each tool is called, then the
    facts and content, or the error. Uses its own database session.
    """
    db = session_factory()
    try:
        report = db.get(Report, report_id)
        ctx = ReportContext(db, report.period_start, report.period_end, today=today)

        def on_step(step):
            report.trail = report.trail + [step]   # reassigned, so SQLAlchemy saves it
            db.commit()

        def on_usage(input_tokens, output_tokens):
            report.input_tokens += input_tokens
            report.output_tokens += output_tokens

        try:
            draft = run_report(ctx, client, on_step, on_usage)
            report.content = draft.model_dump()
            report.status = ReportStatus.DONE
        except ReportFailed as e:
            report.error = str(e)
            report.status = ReportStatus.FAILED
        except Exception as e:   # e.g. Claude unreachable: the page shows the report as failed
            report.error = friendly_error(e)
            report.status = ReportStatus.FAILED
        report.facts = ctx.facts.as_list()
        db.commit()
    finally:
        db.close()


def friendly_error(e: Exception) -> str:
    import anthropic
    if isinstance(e, anthropic.APIConnectionError):
        return 'Could not reach Claude. Check the internet connection and try again.'
    if isinstance(e, anthropic.APIStatusError):
        return f'Claude returned an error ({e.status_code}). Try again in a minute.'
    return f'The report stopped with an error: {e}'


def report_out(report: Report) -> dict:
    """A report for the page: each item's cited facts filled in, with the numbers formatted by code."""
    facts = {f['id']: {**f, 'display': format_value(f['value'], f['unit'])} for f in report.facts}

    def items(section):
        return [{**item, 'facts': [facts[f] for f in item['facts'] if f in facts]}
                for item in (report.content or {}).get(section, [])]

    return {
        'id': report.id, 'created_at': report.created_at, 'status': report.status.value,
        'period_start': report.period_start, 'period_end': report.period_end,
        'trail': report.trail, 'error': report.error,
        'next_steps': items('next_steps'), 'findings': items('findings'),
        'input_tokens': report.input_tokens, 'output_tokens': report.output_tokens,
    }
