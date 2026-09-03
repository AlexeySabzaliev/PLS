# Cursor: без Run / Accept на каждом шаге

## 1. Откройте правильный workspace

**Не** папку `D:\Billings` (OUB) — агент пишет в `D:\PLS` «снаружи» → постоянные Approve.

```
File → Open Workspace from File → D:\PLS\PLS.code-workspace
```

Слева должен быть один корень: **PLS**. Git: `AlexeySabzaliev/PLS`.

Billings (`oub`) открывайте отдельным окном Cursor, только когда нужен эталон.

## 2. Run Mode (один раз)

`Ctrl+Shift+J` → **Cursor Settings** → **Agents** → **Approvals & Execution**

**Run Mode → Run Everything**

Не Auto-review, не Allowlist.

## 3. Перезагрузка

`Ctrl+Shift+P` → **Developer: Reload Window**

## 4. Новый чат

Старый чат мог «застрять» в режиме review. Закройте его, начните **новый Agent-чат** уже в workspace PLS.

## 5. Multitask

Выключите **Multitask Mode** в чате — subagent’ы дают отдельные Run/Approve.

---

## Если Accept на файлах всё ещё есть

- Проверьте: `D:\PLS\.vscode\settings.json` → `inlineDiffs: true` (уже так)
- `Ctrl+Shift+Y` — принять все изменения в файле (Windows)
- Застрявшие phantom diff: Select All → Copy → Undo до исчезновения → Paste

## Если Run на командах всё ещё есть

Значит UI всё ещё не в **Run Everything**. JSON `enableRunEverything` этого не делает — только переключатель в Settings.

## Резервное копирование (prod)

См. [BACKUP.md](./BACKUP.md): `flask pls backup`, `scripts/backup_pls.ps1`, `PLS_BACKUP_DIR`, `PLS_BACKUP_RETENTION`.
