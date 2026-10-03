#!/usr/bin/env python3
"""Генератор синтетических фикстур testdata/claude-home (см. README там же).

Запуск из корня репо:  python3 testdata/gen_fixtures.py testdata/claude-home
"""
import json, os, sys
ROOT = sys.argv[1]
V = "2.1.288"
def uid(sess, n): return f"{sess[:8]}-0000-4000-8000-{n:012d}"
def ts(m, s=0): return f"2026-09-01T10:{m:02d}:{s:02d}.000Z"

class S:
    def __init__(self, sid, cwd, branch="main", agent=None):
        self.sid, self.cwd, self.branch, self.agent = sid, cwd, branch, agent
        self.lines, self.n, self.t = [], 0, 0
    def base(self, typ, parent, **kw):
        self.n += 1; self.t += 1
        d = {"parentUuid": parent, "isSidechain": self.agent is not None}
        if self.agent: d["agentId"] = self.agent
        d.update({"type": typ, "uuid": uid(self.sid if not self.agent else self.agent.replace("afork-","a0000000"), self.n),
                  "timestamp": ts(self.t // 60, self.t % 60), "userType": "external", "entrypoint": "cli",
                  "cwd": kw.pop("cwd", self.cwd), "sessionId": self.sid, "version": V, "gitBranch": self.branch})
        d.update(kw); self.lines.append(d); return d["uuid"]
    def meta(self, **kw): self.lines.append(kw)
    def human(self, parent, text, **kw):
        return self.base("user", parent, message={"role": "user", "content": text},
                         permissionMode="default", origin={"kind": "human"}, promptSource="typed", **kw)
    def asst(self, parent, blocks, mid, model="claude-sonnet-5"):
        u = parent
        for i, b in enumerate(blocks):
            u = self.base("assistant", u, apiBlockIndex=i, requestId="req_"+mid,
                message={"id": "msg_"+mid, "type": "message", "role": "assistant", "model": model,
                         "content": [b], "stop_reason": "tool_use" if b["type"]=="tool_use" else ("end_turn" if i==len(blocks)-1 else None),
                         "stop_sequence": None, "usage": {"input_tokens": 100, "output_tokens": 20,
                         "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}})
        return u
    def tool_result(self, parent, tool_id, text, tur):
        return self.base("user", parent, message={"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": tool_id, "content": text, "is_error": False}]},
            toolUseResult=tur, sourceToolAssistantUUID=parent)
    def turn(self, parent):
        return self.base("system", parent, subtype="turn_duration", durationMs=4200, messageCount=4, isMeta=True)
    def write(self, path, tail=""):
        path = os.path.join(ROOT, path); os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            for l in self.lines: f.write(json.dumps(l, ensure_ascii=False) + "\n")
            f.write(tail)

def head(s):
    s.meta(type="mode", mode="normal", sessionId=s.sid)
    s.meta(type="permission-mode", permissionMode="default", sessionId=s.sid)
def cost(s, usd):
    s.meta(type="cost-state", sessionId=s.sid, totalCostUSD=usd, totalAPIDuration=12000, totalAPIDurationWithoutRetries=12000,
           totalToolDuration=300, totalLinesAdded=3, totalLinesRemoved=1, totalDuration=60000, startTime=1788256800000,
           modelUsage={"claude-sonnet-5": {"inputTokens": 400, "outputTokens": 80}}, hasUnknownModelCost=False)

P = "projects/-home-alice-projects-demo"

# 1. basic
s = S("11111111-1111-4111-8111-111111111111", "/home/alice/projects/demo")
head(s)
u = s.human(None, "Привет! Что делает этот проект?")
a = s.asst(u, [{"type": "thinking", "thinking": "Нужно посмотреть README.", "signature": "sig"},
               {"type": "text", "text": "Это **демо-проект** для тестов cce."}], "basic1")
s.turn(a)
s.meta(type="ai-title", aiTitle="Первый заголовок", sessionId=s.sid)
s.meta(type="last-prompt", lastPrompt="Привет! Что делает этот проект?", leafUuid=a, sessionId=s.sid)
u2 = s.human(a, "Спасибо")
a2 = s.asst(u2, [{"type": "text", "text": "Пожалуйста!"}], "basic2")
s.meta(type="ai-title", aiTitle="Знакомство с демо-проектом", sessionId=s.sid)
s.meta(type="last-prompt", lastPrompt="Спасибо", leafUuid=a2, sessionId=s.sid)
cost(s, 0.0123)
s.write(f"{P}/{s.sid}.jsonl")

# 2. tools: parallel tool_use
s = S("22222222-2222-4222-8222-222222222222", "/home/alice/projects/demo", branch="feature/x")
head(s)
u = s.human(None, "Прочитай a.txt и b.txt")
b1 = s.asst(u, [{"type": "tool_use", "id": "toolu_A", "name": "Read", "input": {"file_path": "/home/alice/projects/demo/a.txt"}}], "tools1")
b2 = s.asst(b1, [{"type": "tool_use", "id": "toolu_B", "name": "Read", "input": {"file_path": "/home/alice/projects/demo/b.txt"}}], "tools1")
s.lines[-1]["apiBlockIndex"] = 1
r1 = s.tool_result(b1, "toolu_A", "aaa", {"type": "text", "file": {"filePath": "/home/alice/projects/demo/a.txt", "content": "aaa"}})
r2 = s.tool_result(b2, "toolu_B", "Error: file not found", "Error: file not found")
s.lines[-1]["parentUuid"] = r1
a = s.asst(r2, [{"type": "text", "text": "a.txt содержит `aaa`, b.txt не найден."}], "tools2")
s.meta(type="ai-title", aiTitle="Чтение файлов", sessionId=s.sid)
s.meta(type="last-prompt", lastPrompt="Прочитай a.txt и b.txt", leafUuid=a, sessionId=s.sid)
s.write(f"{P}/{s.sid}.jsonl")

# 3. branched: user rewound and re-typed prompt
s = S("33333333-3333-4333-8333-333333333333", "/home/alice/projects/demo")
head(s)
u = s.human(None, "Напиши функцию сложения")
a = s.asst(u, [{"type": "text", "text": "function add(a, b) { return a + b }"}], "br1")
x = s.human(a, "Перепиши на Python")
xa = s.asst(x, [{"type": "text", "text": "def add(a, b): return a + b"}], "br2")
s.meta(type="last-prompt", lastPrompt="Перепиши на Python", leafUuid=xa, sessionId=s.sid)
y = s.human(a, "Перепиши на Go")
ya = s.asst(y, [{"type": "text", "text": "func add(a, b int) int { return a + b }"}], "br3")
s.meta(type="ai-title", aiTitle="Функция сложения", sessionId=s.sid)
s.meta(type="last-prompt", lastPrompt="Перепиши на Go", leafUuid=ya, sessionId=s.sid)
s.write(f"{P}/{s.sid}.jsonl")

# 4. cwd change + lossy dir encoding (my_app -> my-app)
s = S("44444444-4444-4444-8444-444444444444", "/home/alice/projects/my_app")
head(s)
u = s.human(None, "Зайди в backend и запусти тесты")
a = s.asst(u, [{"type": "tool_use", "id": "toolu_C", "name": "Bash", "input": {"command": "cd backend && go test ./..."}}], "cwd1")
r = s.tool_result(a, "toolu_C", "ok", {"stdout": "ok", "stderr": "", "interrupted": False, "isImage": False, "noOutputExpected": False})
a2 = s.asst(r, [{"type": "text", "text": "Тесты прошли."}], "cwd2")
for l in s.lines[-2:]: l["cwd"] = "/home/alice/projects/my_app/backend"
s.meta(type="ai-title", aiTitle="Тесты бэкенда", sessionId=s.sid)
s.meta(type="last-prompt", lastPrompt="Зайди в backend и запусти тесты", leafUuid=a2, sessionId=s.sid)
s.write(f"projects/-home-alice-projects-my-app/{s.sid}.jsonl")

# 5. subagent fork
SID = "55555555-5555-4555-8555-555555555555"
s = S(SID, "/home/alice/projects/demo")
head(s)
u = s.human(None, "Запусти форк, пусть проверит тесты")
a = s.asst(u, [{"type": "tool_use", "id": "toolu_D", "name": "Agent", "input": {"subagent_type": "fork", "description": "Проверить тесты", "prompt": "Проверь тесты"}}], "sub1")
r = s.tool_result(a, "toolu_D", "Форк запущен", {"status": "async_launched", "agentId": "afork-0123456789abcdef"})
a2 = s.asst(r, [{"type": "text", "text": "Форк работает в фоне."}], "sub2")
s.meta(type="ai-title", aiTitle="Форк для тестов", sessionId=s.sid)
s.meta(type="last-prompt", lastPrompt="Запусти форк, пусть проверит тесты", leafUuid=a2, sessionId=s.sid)
s.write(f"{P}/{SID}.jsonl")
f = S(SID, "/home/alice/projects/demo", agent="afork-0123456789abcdef")
f.meta(type="fork-context-ref", agentId=f.agent, parentSessionId=SID, parentLastUuid=a, contextLength=3)
fu = f.base("user", None, message={"role": "user", "content": "Проверь тесты"})
f.asst(fu, [{"type": "text", "text": "Все тесты зелёные."}], "fork1")
f.write(f"{P}/{SID}/subagents/agent-afork-0123456789abcdef.jsonl")
with open(os.path.join(ROOT, P, SID, "subagents/agent-afork-0123456789abcdef.meta.json"), "w") as fh:
    json.dump({"agentType": "fork", "isFork": True, "description": "Проверить тесты", "name": "fork",
               "spawnDepth": 1, "requestShape": "background", "requestNonInteractive": False, "model": "inherit"}, fh, ensure_ascii=False)

# 6. robustness: unknown types/fields, service messages, truncated last line (active session)
s = S("66666666-6666-4666-8666-666666666666", "/home/alice/projects/demo")
head(s)
s.meta(type="some-future-type", whatever={"x": 1}, sessionId=s.sid)
c = s.base("user", None, message={"role": "user", "content": "<local-command-caveat>Caveat: generated by local commands.</local-command-caveat>"}, isMeta=True)
c2 = s.base("user", c, message={"role": "user", "content": "<command-name>/model</command-name>\n<command-args></command-args>"})
u = s.human(c2, "Продолжим", futureField=True)
a = s.asst(u, [{"type": "text", "text": "API Error: overloaded"}], "rob1", model="<synthetic>")
s.lines[-1]["isApiErrorMessage"] = True
s.write(f"{P}/{s.sid}.jsonl", tail='{"parentUuid":"' + a + '","isSidechain":false,"type":"user","mess')

# live process registry: session 6 is active
os.makedirs(os.path.join(ROOT, "sessions"), exist_ok=True)
with open(os.path.join(ROOT, "sessions/424242.json"), "w") as fh:
    json.dump({"pid": 424242, "sessionId": s.sid, "cwd": "/home/alice/projects/demo", "startedAt": 1788256800000,
               "version": V, "kind": "interactive", "entrypoint": "cli", "status": "busy", "updatedAt": 1788256900000}, fh)
