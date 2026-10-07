"""Order-paper HTML. The face is the outcome. The reverse is the stage audit."""

from html import escape

from fs_prod_agent.adapters.local.desk_audit import Stage, primer_stages

_SCRIPT = """
(function () {
  var form = document.querySelector("form");
  if (form) {
    form.addEventListener("submit", function () {
      document.body.setAttribute("data-running", "1");
      var note = document.querySelector(".running");
      if (note) note.hidden = false;
    });
  }
  var turn = document.getElementById("turn");
  var front = document.querySelector(".front");
  var back = document.querySelector(".back");
  if (!turn || !front || !back) return;
  var sync = function () {
    var flipped = turn.checked;
    front.inert = flipped;
    back.inert = !flipped;
  };
  turn.addEventListener("change", sync);
  sync();
})();
"""


def render_home(cases: tuple[tuple[str, str], ...], error: str = "") -> str:
    front = _home_front(cases, error)
    back = _audit_back("What each stage will do", primer_stages(), "Nothing has run yet.")
    return _document(front, back)


def render_run(
    question: str,
    outcome: str,
    stages: tuple[Stage, ...],
    cases: tuple[tuple[str, str], ...],
) -> str:
    front = _run_front(question, outcome, cases)
    back = _audit_back("What each stage did", stages, "")
    return _document(front, back)


def render_missing() -> str:
    front = (
        "<h1>Oversight desk</h1>"
        + _rule()
        + '<p class="error" role="alert">That case is not on the paper.</p>'
        + '<p><a href="/">Return to the desk.</a></p>'
    )
    back = _audit_back("What each stage will do", primer_stages(), "Nothing has run yet.")
    return _document(front, back)


def _document(front: str, back: str) -> str:
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Oversight desk</title>"
        '<link rel="stylesheet" href="/static/desk.css">'
        "</head><body>"
        '<p class="running" role="status" hidden>The pipeline is running.</p>'
        '<div class="cloth"><div class="scene">'
        '<div class="turn-row">'
        '<input type="checkbox" id="turn" class="turn-control">'
        '<label for="turn" class="turn-label">'
        '<span class="to-audit">Turn to the audit</span>'
        '<span class="to-answer">Turn to the answer</span>'
        "</label></div>"
        '<div class="stage"><div class="sheet-shadow"><div class="sheet">'
        f'<article class="face front">{front}</article>'
        f'<article class="face back">{back}</article>'
        "</div></div></div></div></div>"
        f"<script>{_SCRIPT}</script>"
        "</body></html>"
    )


def _home_front(cases: tuple[tuple[str, str], ...], error: str) -> str:
    return (
        "<h1>Oversight desk</h1>"
        + _rule()
        + "<p>Ask the desk a question, or open a worked case. It drafts and checks. It does not trade.</p>"
        + "<p>What you type is answered on this sheet. The committee paper is one of the worked cases, "
        + "and it waits for a person.</p>"
        + _form("", error)
        + _cases(cases)
        + _book()
    )


def _run_front(question: str, outcome: str, cases: tuple[tuple[str, str], ...]) -> str:
    return (
        "<h1>Oversight desk</h1>"
        + _rule()
        + f"<h2>{_esc(question)}</h2>"
        + f'<div class="plate"><p>{_esc(outcome)}</p></div>'
        + _form(question, "")
        + _cases(cases)
        + _book()
    )


def _audit_back(heading: str, stages: tuple[Stage, ...], note: str) -> str:
    items = "".join(_stage(stage) for stage in stages)
    lead = f'<p class="note">{_esc(note)}</p>' if note else ""
    return f'<h2>{_esc(heading)}</h2>{lead}<ol class="stages">{items}</ol>'


def _stage(stage: Stage) -> str:
    mark = "ran" if stage.ran else "idle"
    prefix = "" if stage.ran else '<span class="sr">Did not run. </span>'
    return (
        "<li>"
        + f'<h3 class="stage-name {mark}">{prefix}{_esc(stage.name)}</h3>'
        + f"<p>{_esc(stage.did)}</p>"
        + "</li>"
    )


def _form(question: str, error: str) -> str:
    alert = f'<p class="error" role="alert">{_esc(error)}</p>' if error else ""
    return (
        alert
        + '<form method="post" action="/ask">'
        + '<label for="question">Question</label>'
        + '<textarea id="question" name="question" rows="5" maxlength="2000" required>'
        + f"{_esc(question)}</textarea>"
        + '<button type="submit">Ask the desk</button>'
        + "</form>"
    )


def _cases(cases: tuple[tuple[str, str], ...]) -> str:
    items = "".join(f'<li><a href="/case/{_esc(case_id)}">{_esc(request)}</a></li>' for case_id, request in cases)
    return f'<h2>Worked cases</h2><ul class="cases">{items}</ul>'


def _book() -> str:
    return '<p class="book">The book is the fixture for 30 June 2026. The page does not recompute it.</p>'


def _rule() -> str:
    return '<hr class="rule">'


def _esc(text: str) -> str:
    return escape(text, quote=True)
