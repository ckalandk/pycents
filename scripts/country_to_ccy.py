import ssl
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from utils import _compute_hash, _get_stored_hash

ssl_context = ssl._create_unverified_context()

url = "https://raw.githubusercontent.com/unicode-org/cldr/main/common/supplemental/supplementalData.xml"

current_dir = Path(__file__).parent
root_dir = current_dir.parent
output_path = root_dir / "src" / "pycents" / "data"
output_file = output_path / "countries.py"


def fetch_and_generate():
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_xml_path = Path(temp_dir) / "supplementalData.xml"

        print("Downloading CLDR XML to temporary folder...")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, context=ssl_context) as response:
            with open(temp_xml_path, "wb") as f:
                f.write(response.read())

        # Compute hashes to determine if we need to regenerate the Python file
        current_hash = _compute_hash(temp_xml_path)
        # Get the last stored hash from the existing output file
        last_hash = _get_stored_hash(output_file) if output_file.exists() else None
        # If the hashes match, no changes have occurred in the XML data,
        # so we can skip regeneration
        if current_hash == last_hash:
            print("No changes detected in the XML data.")
            return
        print("Parsing XML and extracting active currencies...")
        mapping = parse_cldr_xml(temp_xml_path)

    # Write the Python dictionary file
    print(f"Generating Python data file at {output_file}...")
    write_python_file(mapping, output_file, current_hash)
    print("Datas has been successfully generated and saved.")


def parse_cldr_xml(xml_path: Path) -> dict[str, str]:
    """Extracts a 1:1 mapping of Country Code -> Primary Active Currency."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    country_to_currency: dict[str, str] = {}

    # Locate the region entries inside currencyData
    for region in root.findall(".//currencyData/region"):
        country_code = region.get("iso3166")

        # Skip regions that aren't 2-letter country codes (e.g., '001' for World)
        if not country_code or len(country_code) != 2:
            continue

        # Find the active, primary currency
        for currency in region.findall("currency"):
            # Skip historical currencies
            if "to" in currency.attrib:
                continue

            # Skip non-legal tender or whatever this means
            if currency.get("tender") == "false":
                continue

            # We found the active currency! Break to ignore secondary ones.
            currency_code = currency.get("iso4217")
            if currency_code:
                country_to_currency[country_code] = currency_code
                break

    return country_to_currency


def write_python_file(
    mapping: dict[str, str], output_path: Path, hash_value: str
) -> None:
    """Compile the data into a Python dictionary file."""
    # Ensure the directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# This file is auto-generated from CLDR XML data. Do not edit manually.",
        "# Maps ISO 3166-1 alpha-2 country codes to primary ISO 4217 currency codes.",
        f'\n\n_xml_hash = "{hash_value}"',
        "\n\nCNTRY_TO_PRIMARY_CCY: dict[str, str] = {",
    ]

    # Sort keys alphabetically so Git diffs remain clean when CLDR updates
    for country, currency in sorted(mapping.items()):
        lines.append(f'    "{country}": "{currency}",')

    lines.append("}")
    lines.append("")  # Trailing newline

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    fetch_and_generate()
