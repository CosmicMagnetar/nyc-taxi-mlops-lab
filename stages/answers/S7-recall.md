# S7 recall check: my answers

**1. What MCP standardises that a hand-rolled HTTP API doesn't**
MCP gives every tool the same shape: a client can ask the server what tools exist (names, descriptions, JSON Schema for the arguments), call them in one standard way, and get results or errors back in one format. With a hand-rolled API, the app has to hard-code each endpoint and its request and response, and every new tool needs new app code. Here the assistant lists the tools, shows the schemas to the model, and runs any call the model asks for, and the contract in `contracts/mcp-tools.json` is the one source of truth for the arguments.

**2. Least privilege for a tool that reads a warehouse**
Its database user should be able to read only the table the tool needs (`SELECT` on `marts.zone_hour_stats` and `USAGE` on schema `marts`) and nothing else: no write, no create, no access to the raw `ingest` and `staging` schemas, and a statement timeout. It should not be `labadmin`. Then even a bad query or a tricked tool can only read aggregated statistics. The tool also uses fixed SQL with named parameters, so nothing from the call can change the query.

**3. Indirect prompt injection, and why the model can't be the only defence**
It is when instructions are hidden in data the model reads (a wiki page, a document, a tool result) and the model treats them as if the user or the developer had written them. The model reads everything as text and cannot reliably tell instructions from data, so a clever enough text can steer it. That is why the model cannot be the only thing that stops it: the limits have to be outside the model, in code it cannot talk its way past. Examples here: the allowed-tools list, argument checks in `allow_tool_call`, the read-only database user, and the tool's fixed SQL.

**4. Which of my tools would need human confirmation, and why**
None of my three needs it, because all of them only read: `get_model_info` and `predict_duration` ask serving, and `query_zone_stats` reads one table as a read-only user, so the worst case is a wrong answer. A tool that could write, such as refunding a fare, changing a model alias or editing data, would need a person to confirm it with the arguments shown, because its effect cannot be undone by a better answer.
