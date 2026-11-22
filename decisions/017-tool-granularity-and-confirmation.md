# 017: Tool granularity and confirmation

Stage: S7 · Date: 2026-11-22 · Author: Krishna · Drafted by agent: yes (wording drafted by the agent from the student's choice; the student owns it)

## Choice

The assistant may call all three tools in `contracts/mcp-tools.json`: `get_model_info`, `predict_duration` and `query_zone_stats` (`ALLOWED_TOOLS` in `app/src/rideapp/assistant.py`). None needs a person to confirm it before it runs. `allow_tool_call` still refuses any other tool and any zone argument that is not a short printable name.

## Rejected alternative

Only `predict_duration` and `get_model_info`, with no warehouse access from the assistant. It is the smaller surface, but then the assistant cannot answer "how busy is this zone at 8am", which is a real rider question.

## Why

All three tools only read. `get_model_info` and `predict_duration` ask serving-champion, and `query_zone_stats` runs one fixed SELECT as a database user that can read one table (decision 018). None can change anything, so a wrong or tricked call costs a wasted second and a wrong answer, not damage. A confirmation step would also be awkward here: `/assist` is one request and one answer, so a person in the loop would need a new flow for a harmless read.

The tools are small and each does one thing, so the model chooses by name and the arguments are checked by the tool: zone names become ids through the TLC list (a typo gets suggestions), the hour has a range, and the day is an enum.

If a tool could write (for example refund a fare, or change a model alias), I would want a person to confirm it before it runs, with the arguments shown, and I would give it its own database role.

## What would show this was wrong

- The trace shows the model calling a tool for something the rider did not ask. Then a call needs a stronger check than "the tool is on the list".
- A tool gains a side effect. Then this decision no longer holds and confirmation becomes necessary.
- The extra prompt tokens from the tool definitions (about 1,000) make answers too slow for the value they add.
