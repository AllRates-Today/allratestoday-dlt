# AllRatesToday → dlt pipeline

Load live market exchange rates **and official central-bank / tax-authority rates
(121 central banks + 3 tax authorities)** from [AllRatesToday](https://allratestoday.com) into DuckDB,
Postgres, BigQuery, Snowflake or any other [dlt](https://dlthub.com) destination.

Built on dlt's `rest_api` source, so there is no custom client code to maintain.

## What gets loaded

| Table | Endpoint | Data selector | Notes |
|---|---|---|---|
| `currencies` | `GET /api/v1/symbols` | `currencies` | 160+ supported currencies |
| `market_rates` | `GET /api/v1/rates?source=&target=` | `$` | Mid-market rate for one pair, refreshed every minute (append) |
| `central_banks` | `GET /api/v1/central-banks` | `banks` | Catalogue of every official source (121 central banks + 3 tax authorities + composite), home currency, history depth |
| `official_rates` | `GET /api/v1/central-bank/{bank}/latest` | `rates` | Latest official table per bank (merge on bank + date + pair + type) |
| `official_rates_by_bank` | `GET /api/v1/central-banks/rates?source=&target=` | `banks` | Every bank's official rate for one pair, with min/max/median |

Dated tables (`/api/v1/central-bank/{bank}/{date}`) and time series
(`/api/v1/central-bank/{bank}/history?source=&target=&from=&to=`) follow the same
shape; add them as extra resources when you need backfills.

## Tested output

```
currencies               160 rows
central_banks            125 rows
official_rates           133 rows  (ecb 29, boe 23, rbi 6, cbuae 75 — one row per base/quote/type)
official_rates_by_bank   111 rows  (USD→EUR across every bank, with min/max/median)
market_rates               1 row   (appends one mid-market observation per run)
```

## Quick start

```bash
uv init && uv add "dlt[duckdb]"          # or: pip install "dlt[duckdb]"
cp .dlt/secrets.toml.example .dlt/secrets.toml   # paste your key
python allratestoday_pipeline.py
```

Get a free key at <https://allratestoday.com/register> (300 requests, no card),
or self-issue a 100-call trial key with no account:

```bash
curl -X POST https://allratestoday.com/api/agent/keys \
  -H 'Content-Type: application/json' -d '{"agent":"dlt"}'
```

## Query the data

```python
import duckdb
con = duckdb.connect("allratestoday.duckdb")
print(con.sql("SELECT bank, rate_date, base, quote, value FROM allratestoday_data.official_rates LIMIT 5"))
```

```sql
SELECT bank, rate_date, base, quote, value
FROM allratestoday_data.official_rates
WHERE quote = 'USD'
ORDER BY rate_date DESC;
```

## Keyless alternative

The open endpoints need no key (attribution required, non-commercial):
`/api/open/central-banks`, `/api/open/central-bank/{bank}` (selector `rates`),
`/api/open/reference-rate` (selector `rates`), and the Frankfurter / fixer /
exchangeratesapi compatible shapes under `/api/compat/{provider}/latest`.
Drop the `auth` block from the client config to use them.

## Links

- Docs: <https://allratestoday.com/docs>
- OpenAPI: <https://allratestoday.com/openapi.json>
- Central bank coverage: <https://allratestoday.com/central-bank-rates-api/>
- MCP server (for AI agents): <https://allratestoday.com/api/mcp>

MIT licensed. Rates data is subject to the [AllRatesToday terms](https://allratestoday.com/terms/).
