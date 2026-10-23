"""dlt pipeline for AllRatesToday — market exchange rates plus official
central-bank and tax-authority rates (121 central banks + 3 tax authorities), loaded into DuckDB.

Free key: https://allratestoday.com/register (free, no card)
Self-issued trial key (no account): POST https://allratestoday.com/api/agent/keys
Docs: https://allratestoday.com/docs
"""
import dlt
from dlt.sources.rest_api import RESTAPIConfig, rest_api_resources


@dlt.source(name="allratestoday")
def allratestoday_source(
    api_key: str = dlt.secrets.value,
    banks: list = ("ecb", "boe", "rbi", "cbuae"),
    source: str = "USD",
    target: str = "EUR",
):
    config: RESTAPIConfig = {
        "client": {
            "base_url": "https://allratestoday.com/api/",
            "auth": {"type": "bearer", "token": api_key},
            "paginator": "single_page",
        },
        "resource_defaults": {"write_disposition": "replace"},
        "resources": [
            # --- market rates (mid-market, refreshed every minute) ---
            {
                "name": "currencies",
                "endpoint": {"path": "v1/symbols", "data_selector": "currencies"},
            },
            {
                "name": "market_rates",
                "endpoint": {
                    "path": "v1/rates",
                    "params": {"source": source, "target": target},
                    "data_selector": "$",
                },
                "write_disposition": "append",
            },
            # --- official rates (central banks + tax authorities) ---
            {
                "name": "central_banks",
                "endpoint": {"path": "v1/central-banks", "data_selector": "banks"},
            },
            *[
                {
                    "name": f"official_rates_{bank}",
                    "table_name": "official_rates",
                    "endpoint": {
                        "path": f"v1/central-bank/{bank}/latest",
                        "data_selector": "$",
                    },
                    "write_disposition": "merge",
                    "primary_key": ["bank", "rate_date", "base", "quote", "type"],
                }
                for bank in banks
            ],
            {
                "name": "official_rates_by_bank",
                "endpoint": {
                    "path": "v1/central-banks/rates",
                    "params": {"source": source, "target": target},
                    "data_selector": "banks",
                },
            },
        ],
    }
    def flatten_table(page):
        # one row per (base, quote, type) with the bank and rate_date stamped on
        for rate in page["rates"]:
            yield {**rate, "bank": page["bank"], "rate_date": page["rate_date"]}

    for resource in rest_api_resources(config):
        if resource.table_name == "official_rates":
            resource.add_yield_map(flatten_table)
        yield resource


def load_allratestoday() -> None:
    pipeline = dlt.pipeline(
        pipeline_name="allratestoday",
        destination="duckdb",
        dataset_name="allratestoday_data",
    )
    info = pipeline.run(allratestoday_source())
    print(info)


if __name__ == "__main__":
    load_allratestoday()
