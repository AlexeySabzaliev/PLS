# Эталоны Ariston billing

Полный набор Excel (`Ariston billing 01.2026.xlsx` … `08.2026.xlsx`) **не включён** в репозиторий из-за размера.

## Где взять файлы

1. Скопируйте из Billings: `D:\Billings\backend\tests\fixtures\ariston_billing\`
2. Или укажите путь в `.env`: `ARISTON_BILLING_FIXTURES_PATH=D:\Billings\backend\tests\fixtures\ariston_billing`

## Тесты фазы 4

После портирования `billing/calculator.py` и парсера Excel:

```bash
pytest tests/test_ariston_billing_ref.py -v
```

Сейчас в репозитории только этот README — один небольшой fixture можно добавить при реализации сверки.
