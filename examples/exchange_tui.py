from datetime import date
from decimal import InvalidOperation

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Input, Label, Static

from pycents import Currency, Money, PyCentsError, formatting
from pycents.conversion import DefaultProvider

# Use Babel for locale-aware money formatting.
formatting.use_backend("babel")

# Target currencies to display in our showcase table
WATCHLIST = [
    "EUR",
    "USD",
    "JPY",
    "CZK",
    "DKK",
    "GBP",
    "HUF",
    "PLN",
    "RON",
    "SEK",
    "CHF",
    "ISK",
    "NOK",
    "TRY",
    "AUD",
    "BRL",
    "CAD",
    "CNY",
    "HKD",
    "IDR",
    "ILS",
    "INR",
    "KRW",
    "MXN",
    "MYR",
    "NZD",
    "PHP",
    "SGD",
    "THB",
    "ZAR",
]

base_ccy = "EUR"


class PyCentsExchangeApp(App):
    """Textual TUI showcasing PyCents conversion engine with ECB live rates."""

    CSS = """
    PyCentsExchangeApp {
        background: $boost;
        align: center top;
        padding: 1 2;
    }
    #control-bar {
        height: auto;
        margin-bottom: 1;
    }
    .field-box {
        width: 1fr;
        height: auto;
        margin-right: 1;
    }
    Label {
        text-style: bold;
        margin-bottom: 0;
    }
    DataTable {
        height: 1fr;
        border: heavy $accent;
    }
    #status {
        height: 1;
        color: $text-muted;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Horizontal(id="control-bar"):
            with Vertical(classes="field-box"):
                yield Label("Amount (Major Units):")
                yield Input(id="amount-input")

            with Vertical(classes="field-box"):
                yield Label("Base Currency:")
                yield Input(id="currency-input")

            with Vertical(classes="field-box"):
                yield Label("Date")
                yield Input(
                    placeholder="YYYY-MM-DD",
                    id="asof-input",
                )

        yield DataTable(id="rate-table")
        yield Static("Ready", id="status")
        yield Footer()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Trigger re-calculation whenever amount or base currency changes."""
        if event.input.id == "asof-input":
            try:
                self.provider.rate_date = date.fromisoformat(event.value)
                self.provider.prefetch_rates()
            except ValueError as err:
                self.show_error(str(err))
        self.trigger_refresh()

    def on_mount(self) -> None:
        """Initialize the PyCents provider and setup DataTable columns."""
        amount_input = self.query_one("#amount-input", Input)
        ccy_input = self.query_one("#currency-input", Input)
        date_input = self.query_one("#asof-input", Input)
        with (
            amount_input.prevent(Input.Changed),
            ccy_input.prevent(Input.Changed),
            date_input.prevent(Input.Changed),
        ):
            amount_input.value = "100.00"
            ccy_input.value = base_ccy
            date_input.value = date.today().isoformat()

        # Create the Exchange Rate Provider, use ECB.
        self.provider = DefaultProvider("ECB")
        self.provider.rate_date = date.fromisoformat(date_input.value)
        # Set up the table columns before adding any conversion results.
        table = self.query_one(DataTable)
        table.add_columns(
            "Target Pair",
            "Exchange Rate",
            "Converted Total",
            "Is Cross Rate?",
            "As Of Date",
        )
        # Fetch all available rates in one request and store them in the
        # provider's cache. Subsequent get_rate() calls use this cached data.
        self.provider.prefetch_rates()
        self.trigger_refresh()

    def trigger_refresh(self) -> None:
        # Read the current values entered by the user.
        amount_str = self.query_one("#amount-input", Input).value.strip()
        base_ccy = self.query_one("#currency-input", Input).value.strip().upper()
        asof_str = self.query_one("#asof-input", Input).value.strip()

        if not amount_str or not base_ccy or not asof_str:
            return

        table = self.query_one(DataTable)
        status = self.query_one("#status", Static)

        # Remove the old results immediately so the table reflects
        # the new calculation.
        table.clear()
        table.loading = True
        status.update("Fetching live rates...")

        # Run the conversions in a background thread so the Textual UI
        # remains responsive while the calculations are being performed.
        self.run_conversions(amount_str, base_ccy, asof_str)

    @work(exclusive=True, thread=True)
    def run_conversions(self, amount_str: str, base_ccy: str, asof_str: str) -> None:
        """Runs in a background thread outside the main Textual UI thread"""
        try:
            # Convert the user's input into a Money object.
            base_money = Money.from_major(amount_str, base_ccy)
            asof = date.fromisoformat(asof_str)
            # Calculate one conversion for every currency in the watchlist.
            for target_ccy in WATCHLIST:
                # Skip if the base and quote currency are the same
                if target_ccy == base_ccy:
                    continue
                # Get the Exchange Rate from the provider
                rate_obj = self.provider.get_rate(
                    base_money.currency, Currency.from_code(target_ccy), asof=asof
                )
                # Apply the exchange rate directly to the Money object.
                converted_money = base_money * rate_obj
                # Cross rates are derived from more than one underlying rate,
                # and do not carry any information,
                # so get the date from the first rate in the lineage.
                if rate_obj.info is None and rate_obj.is_cross:
                    first = rate_obj.lineage[0]
                    as_of_str = (
                        str(first.info.asof)
                        if first.info and first.info.asof
                        else "N/A"
                    )
                else:
                    as_of_str = (
                        str(rate_obj.info.asof)
                        if rate_obj.info and rate_obj.info.asof
                        else "N/A"
                    )
                # Prepare the values that will be displayed in the table.
                row = (
                    f"{base_ccy}/{target_ccy}",
                    f"{rate_obj.rate:.4f}",
                    f"{converted_money.round()}",
                    "Yes" if rate_obj.is_cross else "No",
                    as_of_str,
                )
                # Send the completed row back to the main UI thread.
                self.call_from_thread(self.add_row, row)
            # All conversions are finished, so update the status message
            # and remove the loading indicator.
            self.call_from_thread(self.conversions_finished, base_money)

        except (PyCentsError, ValueError, InvalidOperation) as err:
            # Send errors back to the main UI thread as well.
            self.call_from_thread(self.show_error, str(err))

    def add_row(self, row: tuple) -> None:
        # This method runs on the main Textual UI thread.
        # Add the newly calculated conversion to the table.
        table = self.query_one(DataTable)
        table.add_row(*row)

    def conversions_finished(self, base_money: Money) -> None:
        # All rows have been added, so mark the table as ready.
        table = self.query_one(DataTable)
        table.loading = False

        provider_name = self.provider.name
        self.query_one("#status", Static).update(
            f"✅ Provider: {provider_name} | Valid base: {base_money}"
        )

    def show_error(self, err_msg: str) -> None:
        # Display any error in the status area.
        self.query_one("#status", Static).update(
            f"[bold red]Error:[/bold red] {err_msg}"
        )


if __name__ == "__main__":
    app = PyCentsExchangeApp()
    app.run()
