# Формат хранения сессий Claude Code

Результат фазы 0. Формат не документирован Anthropic — всё ниже выведено эмпирически.

**Проверено на:** Claude Code 2.1.252 – 2.1.288 (Linux), 25 сессий, ~6800 записей.
Пометка **[не проверено]** — известно о существовании, но в исследованных данных не встретилось.

## Файловая структура `~/.claude/`

| Путь | Что это | Нужно cce |
|---|---|---|
| `projects/<encoded-dir>/<session-id>.jsonl` | Сессия | да, основное |
| `projects/<encoded-dir>/<session-id>/tool-results/*.txt` | Большие выводы инструментов, вынесенные из JSONL | при sync |
| `projects/<encoded-dir>/<session-id>/subagents/agent-<id>.jsonl` | Транскрипт субагента / форка | да |
| `projects/<encoded-dir>/<session-id>/subagents/agent-<id>.meta.json` | Метаданные субагента (`agentType`, `isFork`, `description`, `model`, …) | да |
| `file-history/<session-id>/<hash>@v<N>` | Бэкапы файлов для `/rewind` | при sync |
| `sessions/<pid>.json` | Живой процесс claude: `pid`, `sessionId`, `cwd`, `status`, `updatedAt` | да, статус «активна» |
| `history.jsonl` | История введённых промптов (`display`, `project`, `sessionId`, `timestamp`) | нет |

### Кодирование имени папки проекта

`<encoded-dir>` = абсолютный путь, где **каждый не-алфавитно-цифровой символ** заменён на `-`:

```
/home/winter/projects/casinoso/devops   → -home-winter-projects-casinoso-devops
/home/winter/projects/pgbouncer_exporter → -home-winter-projects-pgbouncer-exporter
```

Кодировка с потерями (`a/b`, `a-b`, `a_b` → одно и то же) — **декодировать нельзя**. Путь берём из поля `cwd` записей.

### Корень сессии и `cwd`

`cwd` пишется в каждую запись и **меняется по ходу сессии**, если Claude делает `cd` (встречено: сессия из `casinoso/` с записями из `casinoso/server/apps/server`). Каталог запуска (= `<encoded-dir>`) — это `cwd` **первой** записи, у которой он есть. Именно его использует `claude --resume`.

## JSONL: общие правила

- Одна строка = один JSON-объект, у каждого есть `type`.
- Файл append-only. Последняя строка активной сессии может быть **недописанной** → парсер должен игнорировать битую последнюю строку.
- Неизвестные `type` и поля встречаются с каждой версией → игнорировать, не падать.

## Записи-сообщения (входят в дерево)

Типы: `user`, `assistant`, `system`, `attachment`. Общие поля:

| Поле | Описание |
|---|---|
| `uuid` | ID записи |
| `parentUuid` | ID родителя; `null` у корня |
| `isSidechain` | `true` у записей субагента |
| `sessionId` | ID сессии (у субагентов — ID родительской сессии) |
| `timestamp` | ISO 8601 |
| `cwd`, `gitBranch`, `version` | Контекст на момент записи |
| `entrypoint`, `userType` | `cli` / `external` |
| `agentId` | Только у записей субагента |

### `user`

- `message.content` — **строка** (ввод человека) или **массив** блоков (`tool_result`, реже `text`).
- `origin.kind` = `human` и `promptSource` = `typed` | `suggestion_accepted` — признак реального ввода пользователя. `origin.kind` = `task-notification` — системное уведомление.
- `isMeta: true` — служебное, не показывать как реплику.
- Строки, начинающиеся с XML-подобных тегов — служебные обёртки: `<command-name>` (slash-команды), `<bash-input>` / `<bash-stdout>` (режим `!`), `<local-command-caveat>`, `<task-notification>`.
- `toolUseResult` — структурированный результат инструмента (форма зависит от инструмента; бывает просто строкой). `sourceToolAssistantUUID` — запись с `tool_use`.

### `assistant`

- **Одна запись = один блок контента.** Ответ модели из N блоков (`thinking`, `text`, `tool_use`) пишется N записями, связанными цепочкой `parentUuid`, с общим `message.id`; позиция — `apiBlockIndex`.
- `message`: `id`, `model`, `role`, `content[1]`, `stop_reason`, `usage` (токены).
- `message.model = "<synthetic>"` — сообщение сгенерировано самим клиентом (ошибки и т.п.), не моделью.
- Прочее: `requestId`, `effort`, `isApiErrorMessage`.

### `system`

`subtype`: `turn_duration` (`durationMs`, `messageCount`), `away_summary` (`content`), `local_command` (`content`). Обычно `isMeta: true`.
**[не проверено]** `compact_boundary` — граница сжатия контекста (`/compact`), с `logicalParentUuid`; после неё `user` с `isCompactSummary: true`.

### `attachment`

Контекст, подмешанный клиентом (`attachment.type`): `environment`, `date`, `model`, `edited_text_file`, `file`, `skill_listing`, `plan_mode`, `total_tokens_reminder` и др. Для показа пользователю почти не интересны.

## Записи-метаданные (вне дерева)

| `type` | Поля | Смысл |
|---|---|---|
| `ai-title` | `aiTitle` | Автозаголовок. Пишется многократно — актуален **последний** |
| `last-prompt` | `lastPrompt`, `leafUuid` | Последний промпт и **текущий лист** активной ветки |
| `cost-state` | `totalCostUSD`, `totalDuration`, `totalLinesAdded/Removed`, `modelUsage`, … | Накопительная стоимость/статистика, актуальна последняя |
| `mode`, `permission-mode` | `mode`, `permissionMode` | Режимы сессии |
| `agent-name` | `agentName` | Имя сессии (для мультиагентного режима) |
| `file-history-snapshot` | `messageId`, `snapshot.trackedFileBackups` | Снапшот файлов на момент сообщения (для `/rewind`) |
| `file-history-delta` | `messageId`, `trackingPath`, `backup` (`backupFileName`, `realParentDir` — **абсолютный путь**) | Инкремент снапшота |
| `queue-operation` | `operation`, `content` | Очередь промптов, введённых во время работы |
| `bridge-session`, `atis-latch` | — | Внутреннее, игнорировать |
| `fork-context-ref` | `agentId`, `parentSessionId`, `parentLastUuid`, `contextLength` | Первая строка транскрипта форк-субагента: от какой точки родителя он ответвился |

**[не проверено]** `summary` (`summary`, `leafUuid`) — заголовок в старых версиях; `custom-title` — заголовок, заданный пользователем через `/rename`.

## Дерево сообщений и ветки

Записи образуют дерево по `parentUuid`. Несколько детей у одного родителя бывает в двух случаях:

1. **Параллельные вызовы инструментов — НЕ ветка.** Ответ модели с двумя `tool_use`: блок 2 — ребёнок блока 1, и `tool_result` блока 1 — тоже ребёнок блока 1. Признак: один из детей — `user` с `tool_result`, у которого `sourceToolAssistantUUID` = родитель.
2. **Реальная ветка** — пользователь откатился (Esc Esc / `/rewind`) и ввёл промпт заново: два `user`-ребёнка с текстом у одного родителя.

**Активная ветка** = путь от `leafUuid` последней записи `last-prompt` вверх до корня. Если `last-prompt` нет — от последней записи-сообщения в файле.

## Субагенты и форки

- Транскрипт субагента — отдельный файл в `<session-id>/subagents/`, все записи с `isSidechain: true` и `agentId`; `sessionId` = родительская сессия.
- Форк (`agentType: "fork"`, `isFork: true` в `.meta.json`) начинается с `fork-context-ref`, указывающего на точку ответвления в родителе.
- `claude --resume <id> --fork-session` **[не проверено в данных]** создаёт новую сессию-файл с копией истории.

## Абсолютные пути внутри данных (важно для sync)

Абсолютные пути встречаются в: `cwd` всех записей, `tool_use.input` (`file_path` и т.п.), тексте `tool_result`, ссылках на `tool-results/*.txt`, `file-history-delta.backup.realParentDir`, тексте сообщений. Переписывание путей при синхронизации должно учитывать всё это.

## Выводы для парсера cce

- Читать построчно (streaming), битые строки пропускать, неизвестные типы игнорировать.
- Для списка сессий достаточно: корневой `cwd`, первый/последний `timestamp`, последний `ai-title` (или `custom-title`), последний `gitBranch`, число реплик человека, последний `cost-state`, размер файла.
- Для списка можно не парсить `message` целиком — декодировать только «шапку» записи.
- Активность сессии — по `~/.claude/sessions/*.json` (`sessionId` + живой `pid`).

## Фикстуры

`testdata/claude-home/` — синтетический фейковый `~/.claude` (не из реальных сессий: в них секреты и личные пути). Каждая сессия покрывает один кейс, см. `testdata/claude-home/README.md`.
