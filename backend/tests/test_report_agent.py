"""
Tests for the report agent's loop and checks (report_agent.py), with a scripted
fake Claude: each test lists what "Claude" replies, turn by turn, and checks
what the loop does with it. No real API calls.
"""

from datetime import date
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import sessionmaker

import main
import report_agent
from models import DishType, Report, ReportStatus
from report_agent import LAST_CALL, MAX_TOOL_CALLS, MAX_TURNS_OVER_LIMIT, ReportFailed, check_report, report_out, run_report, run_report_job
from report_tools import ReportContext

SEPTEMBER = (date(2026, 9, 1), date(2026, 9, 30))
TODAY = date(2026, 9, 25)


# --- A scripted fake Claude ------------------------------------------------------

def tool_use(name, tool_input=None, id=None):
    return SimpleNamespace(type='tool_use', name=name, input=tool_input or {}, id=id or f'tu_{name}')


def reply(*blocks):
    stop = 'tool_use' if any(b.type == 'tool_use' for b in blocks) else 'end_turn'
    return SimpleNamespace(content=list(blocks), stop_reason=stop,
                           usage=SimpleNamespace(input_tokens=100, output_tokens=20))


def text(words):
    return SimpleNamespace(type='text', text=words)


class FakeClaude:
    """Replies with the scripted turns in order, and remembers every request it was sent."""

    def __init__(self, *turns):
        self.turns = list(turns)
        self.requests = []
        self.messages = self   # so the loop can call client.messages.create(...)

    def create(self, **request):
        # Copied, because the loop keeps appending to the same list.
        self.requests.append({**request, 'messages': list(request['messages'])})
        return self.turns.pop(0)


def good_report(facts=('f1',)):
    item = {'title': 'Push Diavola on the specials board', 'detail': 'It earns the most per plate.', 'facts': list(facts)}
    return {'next_steps': [item], 'findings': [{**item, 'title': 'Contribution rose'}]}


@pytest.fixture
def menu(add_dish, cost_item, add_sales):
    # As in test_report_tools: Margherita margin £8, Diavola £10; August and September sales.
    margherita = add_dish('Margherita', 10.00, DishType.MAIN, recipe=[(cost_item, 2)])
    diavola = add_dish('Diavola', 12.00, DishType.MAIN, recipe=[(cost_item, 2)])
    add_sales(margherita, 20, date(2026, 8, 3))
    add_sales(diavola, 10, date(2026, 8, 3))
    add_sales(margherita, 30, date(2026, 9, 7))
    add_sales(diavola, 10, date(2026, 9, 12))


@pytest.fixture
def ctx(db, menu):
    return ReportContext(db, *SEPTEMBER, today=TODAY)


# --- The checks --------------------------------------------------------------------

def test_a_report_that_cites_real_facts_and_has_no_digits_passes():
    draft, problems = check_report(good_report(), {'f1'}, ['Diavola'])
    assert problems == []
    assert draft.next_steps[0].facts == ['f1']


def test_a_number_in_the_text_is_rejected():
    raw = good_report()
    raw['next_steps'][0]['detail'] = 'Worth £1,089 a month.'
    draft, problems = check_report(raw, {'f1'}, [])
    assert draft is None
    assert problems == ['next_steps 1 ("Push Diavola on the specials board") detail contains a number; cite the fact id instead']


def test_a_made_up_fact_id_is_rejected():
    _, problems = check_report(good_report(facts=('f1', 'f99')), {'f1'}, [])
    assert "cites facts that don't exist: f99" in problems[0]


def test_a_dish_name_with_a_digit_is_allowed():
    raw = good_report()
    raw['next_steps'][0]['title'] = 'Promote the Pizza 12in'
    assert check_report(raw, {'f1'}, ['Pizza 12in'])[1] == []


def test_an_item_citing_no_facts_is_rejected():
    raw = good_report()
    raw['findings'][0]['facts'] = []
    assert check_report(raw, {'f1'}, [])[0] is None


# --- The loop ----------------------------------------------------------------------

def test_the_loop_runs_the_tools_claude_asks_for_then_returns_the_report(ctx):
    claude = FakeClaude(
        reply(text('Starting with the headline figures.'), tool_use('period_summary')),
        reply(tool_use('dish_detail', {'dish': 'Diavola'})),
        reply(tool_use('write_report', good_report(facts=('f1', 'f12')))),
    )
    steps = []
    draft = run_report(ctx, claude, on_step=steps.append)

    assert [s['label'] for s in steps] == ['Reading the headline figures', 'Looking at Diavola', 'Writing the report']
    assert draft.findings[0].facts == ['f1', 'f12']
    # Claude was sent each tool's result: the facts it can cite
    sent = claude.requests[1]['messages'][-1]['content'][0]
    assert sent['tool_use_id'] == 'tu_period_summary'
    assert '[f1] Contribution' in sent['content']


def test_a_report_with_a_number_goes_back_once_to_be_fixed(ctx):
    cheating = good_report()
    cheating['next_steps'][0]['detail'] = 'Worth £657.'
    claude = FakeClaude(
        reply(tool_use('period_summary')),
        reply(tool_use('write_report', cheating, id='tu_1')),
        reply(tool_use('write_report', good_report(), id='tu_2')),
    )
    draft = run_report(ctx, claude)

    assert draft.next_steps[0].detail == 'It earns the most per plate.'
    feedback = claude.requests[2]['messages'][-1]['content'][0]
    assert feedback['is_error'] is True
    assert 'contains a number' in feedback['content']


def test_breaking_the_rules_twice_fails_the_report(ctx):
    cheating = good_report(facts=('f404',))
    claude = FakeClaude(reply(tool_use('write_report', cheating)), reply(tool_use('write_report', cheating)))
    with pytest.raises(ReportFailed, match='broke the rules twice'):
        run_report(ctx, claude)


def investigations(n, start=0):
    return [reply(tool_use('sales_pattern', {'by': 'weekday'}, id=f'tu_{i}')) for i in range(start, start + n)]


def test_after_the_tool_limit_claude_is_told_to_write_and_more_tools_are_refused(ctx):
    claude = FakeClaude(*investigations(MAX_TOOL_CALLS + 1), reply(tool_use('write_report', good_report())))
    run_report(ctx, claude)

    last_allowed = claude.requests[MAX_TOOL_CALLS]['messages'][-1]['content']
    assert last_allowed[-1] == {'type': 'text', 'text': LAST_CALL}
    refused = claude.requests[MAX_TOOL_CALLS + 1]['messages'][-1]['content'][0]
    assert refused['is_error'] is True
    assert refused['content'] == 'No more investigation: call write_report now.'


def test_investigating_on_and_on_past_the_limit_fails_the_report(ctx):
    claude = FakeClaude(*investigations(MAX_TOOL_CALLS + MAX_TURNS_OVER_LIMIT + 1))
    with pytest.raises(ReportFailed, match='kept investigating'):
        run_report(ctx, claude)


def test_thinking_goes_back_to_claude_unchanged(ctx):
    thought = SimpleNamespace(type='thinking', thinking='Start with the summary.', signature='sig123')
    claude = FakeClaude(reply(thought, tool_use('period_summary')), reply(tool_use('write_report', good_report())))
    run_report(ctx, claude)
    sent_back = claude.requests[1]['messages'][1]['content'][0]
    assert sent_back == {'type': 'thinking', 'thinking': 'Start with the summary.', 'signature': 'sig123'}


def test_stopping_without_a_report_gets_one_reminder(ctx):
    claude = FakeClaude(reply(text('All looks fine.')), reply(tool_use('period_summary')),
                        reply(tool_use('write_report', good_report())))
    run_report(ctx, claude)
    assert claude.requests[1]['messages'][-1] == {'role': 'user', 'content': 'Finish by calling write_report.'}

    claude = FakeClaude(reply(text('All looks fine.')), reply(text('Really, all fine.')))
    with pytest.raises(ReportFailed, match='without writing'):
        run_report(ctx, claude)


# --- The background job and what the page gets -----------------------------------------

def test_the_job_saves_the_trail_facts_and_report(engine, db, menu):
    report = Report(period_start=SEPTEMBER[0], period_end=SEPTEMBER[1])
    db.add(report)
    db.commit()
    claude = FakeClaude(reply(tool_use('period_summary')), reply(tool_use('write_report', good_report())))

    run_report_job(report.id, sessionmaker(bind=engine), claude, today=TODAY)
    db.refresh(report)

    assert report.status == ReportStatus.DONE
    assert [s['tool'] for s in report.trail] == ['period_summary', 'write_report']
    assert (report.input_tokens, report.output_tokens) == (200, 40)
    out = report_out(report)
    # The page gets each cited fact with its number formatted by code: f1 is September's £340 contribution
    assert out['next_steps'][0]['facts'][0]['display'] == '£340'


def test_a_failed_job_keeps_its_reason(engine, db, menu):
    report = Report(period_start=SEPTEMBER[0], period_end=SEPTEMBER[1])
    db.add(report)
    db.commit()
    claude = FakeClaude(reply(text('Done.')), reply(text('Done.')))

    run_report_job(report.id, sessionmaker(bind=engine), claude, today=TODAY)
    db.refresh(report)
    assert report.status == ReportStatus.FAILED
    assert 'without writing' in report.error


def test_a_report_whose_job_has_gone_is_marked_interrupted(db):
    report = Report(period_start=SEPTEMBER[0], period_end=SEPTEMBER[1])   # running, but no thread
    db.add(report)
    db.commit()
    out = main.get_report(report.id, db)
    assert out['status'] == 'failed'
    assert out['error'].startswith('Interrupted')


def test_a_report_needs_sales_in_the_period(db, monkeypatch):
    monkeypatch.setattr(report_agent, 'client', lambda: pytest.fail('Claude should not be called'))
    with pytest.raises(main.HTTPException) as e:
        main.start_report(*SEPTEMBER, db=db)
    assert e.value.status_code == 422
