# Schedules Sync

Обновляет расписание сотрудников в `schedules.xlsm`.

## Структура xlsm

Один лист, две таблицы, разделённые пустой строкой.

### Таблица 1
- 2-row header + data rows
- Col A: № (с 1), Col B: ФИО, Col C+: часы/статусы по дням

### Таблица 2
- 1-row header (текстовый заголовок, не колонки) + data rows
- Col A: № (с 1), Col B: ФИО

## normalize_fio()
1. `\xa0` → пробел
2. `re.sub(r'\s+', ' ')` — схлопывание пробелов
3. `.strip()`
4. `ё→е`, `Ё→Е`

## Режим `diff`

Full outer join списков ФИО из schedules.xlsm и employees.docx:
- совпавшие — default (без цвета)
- только в schedule — RED
- только в employees — GREEN

## Парсинг xlsm
- Пустая строка — разделитель таблиц (первая встреченная)
- Table 1: данные rows[2:sep_idx]
- Table 2: данные rows[sep_idx+2:]
- Возвращает: `tables[].employees[].{row_num, fio_raw, fio}`

## Единый список (xlsm)
- `get_all_employees()` — объединяет обе таблицы, сортирует по `fio`
- Каждый employee содержит `table_index` (0 или 1)

## Парсинг docx
- Одна таблица, первая строка — заголовок
- Col 1 (index 1): ФИО (trailing `,` удаляется)
- Col 2 (index 2): метка
- Сортировка по `fio`
- `parse_employees()` → `[{fio_raw, fio, label}]`
