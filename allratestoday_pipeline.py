"""dlt pipeline for AllRatesToday — market exchange rates plus official
central-bank and tax-authority rates (121 sources), loaded into DuckDB.

Free key: https://allratestoday.com/register (300 requests, no card)
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
                        "data_selector": "rates",
                    },
                    "write_disposition": "merge",
                    "primary_key": ["bank", "rate_date", "base", "quote", "type"],
                    "columns": {"bank": {"data_type": "text"}},
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
    for resource in rest_api_resources(config):
        if resource.name.startswith("official_rates_") and resource.name != "official_rates_by_bank":
            bank = resource.name.removeprefix("official_rates_")
            resource.add_map(lambda row, b=bank: {**row, "bank": b})
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
