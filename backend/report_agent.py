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
  - At most MAX_TOOL_CALLS investigations; then Claude is told to write, further
    tool calls are refused, and after MAX_TURNS_OVER_LIMIT such turns it fails.
    (Sonnet 5 thinks before answering, and with thinking on the API doesn't allow
    forcing a tool with tool_choice, so the limit is enforced this way.)
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
MAX_TURNS_OVER_LIMIT = 3
LAST_CALL = 'That was the last investigation. Call write_report next.'

SYSTEM = """You are an experienced restaurant consultant reviewing a small UK restaurant's menu \
performance for its owner. You have tools that read the restaurant's own data. Investigate like a \
good manager: start with period_summary, follow anything surprising (a margin that fell, a dish that \
moved quadrant, a price rise, a busy or quiet day), and check data_gaps before trusting a conclusion.

Finish by calling write_report with:
- next_steps: the few things the owner should do next, most valuable first. Concrete and practical, \
in kitchen language (reprice, re-engineer the recipe, feature it on the specials board, check the \
supplier invoice), not generic advice.
- findings: what you found that explains the figures. Each finding adds something the next steps \
don't already say (the why behind them, or something worth knowing); don't repeat a next step as a finding.

The numbers rule, which is checked by code: never write a number, digit, price or percentage in any \
title or detail. Instead cite the ids of the facts that support each item (e.g. ["f7", "f13"]); the \
page shows those numbers next to your words. Write "rose", "fell", "the biggest", "about a third" \
style words only when a cited fact shows it. Only use facts the tools returned. Cite the two to four \
facts that matter most for each item (four at most, checked by code), and only facts that directly back \
that item's words: never a loosely related fact to fill the space. If no fact backs an item, leave the \
item out. Dish names are fine as they are.

Write to the owner about their restaurant. Next steps are things to do in the restaurant (on the menu, \
the pass, the specials board, with suppliers or staff), never requests for more data or analysis, and \
never mention the tools, the app or this report. Only mention a gap in the data as a finding, in plain \
words, when it changes how the figures should be read (e.g. most costs are still estimates).

Only claim what the data shows. It has no information on how customers would react to a price change, \
why a dish sells, or what competitors charge, so don't say a change will or won't affect demand: say \
what to try and what to watch. Compare like with like (a short week against a full one is not a fall).

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
    facts: list[str] = Field(min_length=1, max_length=4)   # fact ids, e.g. ["f7", "f13"]: the ones that matter most


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
                               'facts': {'type': 'array', 'items': {'type': 'string'}, 'minItems': 1, 'maxItems': 4}},
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
        by = tool_input.get('by', '?')
        return 'Sales by dish, weekdays against weekends' if by == 'weekday_by_dish' else f'Sales by {by}'
    return {'period_summary': 'Reading the headline figures', 'price_changes': 'Checking ingredient prices',
            'data_gaps': 'Checking for gaps in the data', 'business_checks': 'Running the business checks',
            'write_report': 'Writing the report'}.get(name, name)


def as_dict(block) -> dict | None:
    """
    An API content block as plain data, to send back in the next request.
    Thinking blocks must go back unchanged (with their signature), or the API
    refuses the next request.
    """
    if block.type == 'tool_use':
        return {'type': 'tool_use', 'id': block.id, 'name': block.name, 'input': block.input}
    if block.type == 'text':
        return {'type': 'text', 'text': block.text}
    if block.type == 'thinking':
        return {'type': 'thinking', 'thinking': block.thinking, 'signature': block.signature}
    if block.type == 'redacted_thinking':
        return {'type': 'redacted_thinking', 'data': block.data}
    return None


class ReportFailed(Exception):
    pass


def run_report(ctx: ReportContext, client, on_step: Callable[[dict], None] = lambda step: None,
               on_usage: Callable[[int, int], None] = lambda i, o: None, focus: str | None = None) -> ReportDraft:
    """
    The agent loop. `client` is an Anthropic client (or a scripted fake in tests).
    Calls on_step with each tool call as it happens, for the live trail. `focus` is
    the owner's optional question, added to the brief.
    Returns the checked draft, or raises ReportFailed.
    """
    dish_names = [d.name for d in ctx.db.query(Dish).all()]
    tools = tool_definitions() + [WRITE_REPORT]
    brief = (f'Write the report for {describe(ctx.start, ctx.end)}, compared with '
             f'{describe(ctx.prev_start, ctx.prev_end)}. Today is {ctx.today:%d %B %Y}.')
    if focus:
        # The owner's own words, marked off from the instructions. The numbers rule
        # and the checks still apply to the answer.
        brief += ('\n\nThe owner asked the report to focus on this:\n<focus>\n' + focus + '\n</focus>\n'
                  'Investigate it first and answer it in the report as far as the data allows, citing the facts. '
                  'If the data cannot answer part of it, say so plainly in a finding (citing the closest facts).')
    messages = [{'role': 'user', 'content': brief}]
    tool_calls = 0
    fixes_left = MAX_FIX_ATTEMPTS
    nudged = False
    turns_over_limit = 0

    while True:
        reply = client.messages.create(model=MODEL, max_tokens=16000, system=SYSTEM, tools=tools, messages=messages)
        usage = getattr(reply, 'usage', None)
        if usage:
            on_usage(usage.input_tokens, usage.output_tokens)
        messages.append({'role': 'assistant', 'content': [d for d in map(as_dict, reply.content) if d]})

        uses = [b for b in reply.content if b.type == 'tool_use']
        if not uses:
            # Claude stopped without writing the report: remind it once.
            if nudged:
                raise ReportFailed('Claude stopped without writing the report.')
            nudged = True
            messages.append({'role': 'user', 'content': 'Finish by calling write_report.'})
            continue

        if tool_calls >= MAX_TOOL_CALLS and any(u.name != 'write_report' for u in uses):
            turns_over_limit += 1
            if turns_over_limit > MAX_TURNS_OVER_LIMIT:
                raise ReportFailed('Claude kept investigating after the limit without writing the report.')
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
        if tool_calls >= MAX_TOOL_CALLS:
            results.append({'type': 'text', 'text': LAST_CALL})
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
            draft = run_report(ctx, client, on_step, on_usage, focus=report.focus)
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
        'period_start': report.period_start, 'period_end': report.period_end, 'focus': report.focus,
        'trail': report.trail, 'error': report.error,
        'next_steps': items('next_steps'), 'findings': items('findings'),
        'input_tokens': report.input_tokens, 'output_tokens': report.output_tokens,
    }
