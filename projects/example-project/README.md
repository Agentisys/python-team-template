# example-project

An example of the standard project shape: a daily check for stock items at or below their
reorder level. Copy the shape, not the code. Delete this folder once your first real
project exists (see [projects/README.md](../README.md#removing-the-example-project)).

| | |
| --- | --- |
| **Owner** | `@your-org/python-team` |
| **Jobs** | `jobs/low_stock.py` |
| **Schedule** | Daily 05:30 |
| **Reads** | A stock CSV (`--input`: `sku,on_hand,reorder_level`) |
| **Writes** | Low-stock CSV (`--output`) |
| **Settings** | None beyond the shared ones in `.env.example` |
| **Secrets** | None |
| **Depends on** | `team-utils` only (standard library otherwise) |

## Run it

```bash
uv run --package example-project projects/example-project/jobs/low_stock.py \
    --input stock.csv --output output/low_stock.csv
```

## Schedule it (on the server)

```powershell
.\deploy\windows\register_task.ps1 -TaskName "Example - low stock" -Package example-project `
    -Script "projects\example-project\jobs\low_stock.py" `
    -ScriptArguments '--input "D:\data\stock.csv" --output "D:\data\low_stock.csv"' `
    -At "05:30" -ServiceAccount "DOMAIN\svc-pyjobs$"
```

## Test it

```bash
uv run pytest projects/example-project
```
