import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
import pandas as pd


# ============================================================
# Configuration
# ============================================================

OPENFIGI_BASE_URL = "https://api.openfigi.com"
OPENFIGI_API_KEY = ""  # Add your API key here


# ============================================================
# API Helper
# ============================================================

def api_call(
    path: str,
    data=None,
    method: str = "POST",
):
    """
    Make an API call to OpenFIGI.
    """

    headers = {
        "Content-Type": "application/json"
    }

    if OPENFIGI_API_KEY:
        headers["X-OPENFIGI-APIKEY"] = OPENFIGI_API_KEY

    request = urllib.request.Request(
        url=urllib.parse.urljoin(OPENFIGI_BASE_URL, path),
        data=data and json.dumps(data).encode("utf-8"),
        headers=headers,
        method=method,
    )

    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


# ============================================================
# Utility Functions
# ============================================================

def chunk_list(lst, size):
    """
    Yield chunks from a list.
    """

    for i in range(0, len(lst), size):
        yield lst[i:i + size]


# ============================================================
# Mapping Logic
# ============================================================

def map_isins_to_dataframe(
    isin_list,
    chunk_size=10,
    sleep_seconds=30,
):
    """
    Convert a list of ISINs into a DataFrame containing
    OpenFIGI mapping results.
    """

    rows = []

    mapping_requests = [
        {
            "idType": "ID_ISIN",
            "idValue": isin,
            "exchCode": "IN",
        }
        for isin in isin_list
    ]

    total_chunks = (
        len(mapping_requests) + chunk_size - 1
    ) // chunk_size

    for chunk_number, request_chunk in enumerate(
        chunk_list(mapping_requests, chunk_size),
        start=1,
    ):

        print(
            f"Processing chunk "
            f"{chunk_number}/{total_chunks} "
            f"({len(request_chunk)} securities)"
        )

        response_chunk = api_call(
            "/v3/mapping",
            request_chunk,
        )

        for request, response in zip(
            request_chunk,
            response_chunk,
        ):

            isin = request["idValue"]

            if response.get("data"):

                for match in response["data"]:

                    rows.append(
                        {
                            "isin": isin,
                            "requested_exchCode": request["exchCode"],
                            "figi": match.get("figi"),
                            "name": match.get("name"),
                            "ticker": match.get("ticker"),
                            "exchCode": match.get("exchCode"),
                            "compositeFIGI": match.get(
                                "compositeFIGI"
                            ),
                            "shareClassFIGI": match.get(
                                "shareClassFIGI"
                            ),
                            "securityType": match.get(
                                "securityType"
                            ),
                            "securityType2": match.get(
                                "securityType2"
                            ),
                            "marketSector": match.get(
                                "marketSector"
                            ),
                            "securityDescription": match.get(
                                "securityDescription"
                            ),
                            "warning": None,
                        }
                    )

            else:

                rows.append(
                    {
                        "isin": isin,
                        "requested_exchCode": request["exchCode"],
                        "figi": None,
                        "name": None,
                        "ticker": None,
                        "exchCode": None,
                        "compositeFIGI": None,
                        "shareClassFIGI": None,
                        "securityType": None,
                        "securityType2": None,
                        "marketSector": None,
                        "securityDescription": None,
                        "warning": response.get(
                            "warning"
                        ),
                    }
                )

        if chunk_number < total_chunks:
            print(
                f"Sleeping for {sleep_seconds} seconds..."
            )
            time.sleep(sleep_seconds)

    df = pd.DataFrame(rows)

    # -----------------------------------------------------------------
    # Convenience column for Yahoo Finance
    # NOTE:
    # OpenFIGI ticker is NOT guaranteed to match NSE ticker.
    # Validate before production use.
    # -----------------------------------------------------------------

    df["yahoo_ticker"] = (
        df["ticker"]
        .fillna("")
        .astype(str)
        + ".NS"
    )

    df.loc[
        df["ticker"].isna(),
        "yahoo_ticker",
    ] = None

    return df


# ============================================================
# Main
# ============================================================

def main():
    base_dir = Path(__file__).parent.parent
    holdings_file = (
        base_dir / "data" / "processed" / "hdfc_flexi_fund_holding_data.xlsx"
    )

    holdings_df = pd.read_excel(
        holdings_file
    )

    isin_list = (
        holdings_df["ISIN"]
        .dropna()
        .unique()
        .tolist()
    )

    print(
        f"Found {len(isin_list)} unique ISINs."
    )

    mapping_df = map_isins_to_dataframe(
        isin_list=isin_list,
        chunk_size=10,
        sleep_seconds=30,
    )

    successful_df = mapping_df[
        mapping_df["figi"].notna()
    ]

    failed_df = mapping_df[
        mapping_df["figi"].isna()
    ]

    print("\nSummary")
    print("-" * 50)
    print(
        f"Successful mappings: "
        f"{len(successful_df)}"
    )
    print(
        f"Failed mappings: "
        f"{len(failed_df)}"
    )

    mapping_df.to_csv(
        base_dir / "data" / "processed" / "openfigi_mapping_results.csv",
        index=False,
    )

    failed_df.to_csv(
        base_dir / "data" / "processed" / "openfigi_mapping_failures.csv",
        index=False,
    )

    print(
        "\nSaved:"
        "\n- openfigi_mapping_results.csv"
        "\n- openfigi_mapping_failures.csv"
    )


if __name__ == "__main__":
    main()