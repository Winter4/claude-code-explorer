# Фикстуры: фейковый `~/.claude`

Синтетические данные в формате Claude Code 2.1.288 (см. `docs/session-format.md`).
Структура повторяет `~/.claude`, поэтому тесты могут подставлять эту папку вместо настоящей.
Реальные сессии сюда не кладём: в них секреты и личные пути.

Генерируются скриптом `testdata/gen_fixtures.py` — правим его и перезапускаем, руками JSONL не редактируем:

```bash
python3 testdata/gen_fixtures.py testdata/claude-home
```

| Сессия | Проект (`cwd`) | Кейс |
|---|---|---|
| `1111…` | `/home/alice/projects/demo` | Базовая: thinking + text одного `message.id` в двух записях, `turn_duration`, несколько `ai-title` (актуален последний), `cost-state` |
| `2222…` | `/home/alice/projects/demo` | Параллельные `tool_use` → псевдо-ветка (не настоящая); `toolUseResult` строкой (ошибка); ветка git `feature/x` |
| `3333…` | `/home/alice/projects/demo` | Настоящая ветка: откат и повторный промпт. Активная ветка «Go» по `leafUuid` последнего `last-prompt`. `/rename`: два `custom-title` (актуален последний, приоритетнее `ai-title`), sidecar `custom-title.json`, `tag` |
| `4444…` | `/home/alice/projects/my_app` | `cwd` меняется по ходу сессии (`cd backend`); кодирование с потерями `my_app` → `-my-app` |
| `5555…` | `/home/alice/projects/demo` | Форк-субагент в `subagents/` с `.meta.json` и `fork-context-ref` |
| `6666…` | `/home/alice/projects/demo` | Устойчивость: неизвестный `type` и поля, служебные `<command-name>` и `isMeta`, `<synthetic>` ошибка API, **недописанная последняя строка**; активна (`sessions/424242.json`) |
