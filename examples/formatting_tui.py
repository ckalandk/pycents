from typing import Literal, cast

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Header,
    Input,
    Label,
    RadioButton,
    RadioSet,
    Select,
    Static,
)

from pycents import Money, formatting
from pycents.formatting import local_format

# Required for localization
formatting.use_backend("babel")


class LabeledField(Vertical):
    """A reusable container with a Label stacked above another widget."""

    DEFAULT_CSS = """
    LabeledField {
        height: auto;
        width: 1fr;
    }
    LabeledField Label {
        text-style: bold;
        color: cyan;
        margin-bottom: 1;
    }
    """

    def __init__(
        self,
        label_text: str,
        widget: Widget,
        id: str | None = None,
        classes: str | None = None,
    ):
        super().__init__(id=id, classes=classes)
        self.label_text = label_text
        self.inner_widget = widget

    def compose(self) -> ComposeResult:
        yield Label(self.label_text)
        yield self.inner_widget


class NumberSpinner(Horizontal):
    """A simple number spinner widget with up and down buttons."""

    DEFAULT_CSS = """
    NumberSpinner {
        height: 3;
    }
    NumberSpinner Button {
        min_width: 5;
    }
    NumberSpinner Input {
        width: 10;
        text-align: center;
    }
    """

    class Changed(Message):
        def __init__(self, value: int) -> None:
            super().__init__()
            self.value = value

    def __init__(
        self,
        value: int = 1,
        min_val: int = 1,
        max_val: int = 100,
        id: str | None = None,
    ):
        super().__init__(id=id)
        self.value = value
        self.min_val = min_val
        self.max_val = max_val

    def compose(self) -> ComposeResult:
        yield Button("-", id="decrease", variant="error")
        yield Input(str(self.value), id="value-input")
        yield Button("+", id="increase", variant="success")

    def on_mount(self) -> None:
        self.query_one("#value-input", Input).disabled = True
        self.query_one("#value-input", Input).value = str(self.value)

    @on(Button.Pressed)
    def handle_button(self, event: Button.Pressed) -> None:
        if event.button.id == "increase":
            self.value = min(self.max_val, self.value + 1)
        elif event.button.id == "decrease":
            self.value = max(self.min_val, self.value - 1)

        self.query_one("#value-input", Input).value = str(self.value)
        self.post_message(self.Changed(self.value))


locales = LabeledField(
    "🌍 Target Locale:",
    Select(
        [
            ("en_US (US English)", "en_US"),
            ("fr_FR (France)", "fr_FR"),
            ("de_DE (Germany)", "de_DE"),
            ("ar_DZ (Algeria)", "ar_DZ"),
            ("ja_JP (Japan)", "ja_JP"),
            ("en_GB (UK English)", "en_GB"),
            ("es_ES (Spain)", "es_ES"),
            ("zh_CN (China)", "zh_CN"),
        ],
        value="en_US",
        id="locale",
    ),
)

currencies = LabeledField(
    "💵 Currency:",
    Select(
        [
            ("USD ($)", "USD"),
            ("EUR (€)", "EUR"),
            ("GBP (£)", "GBP"),
            ("JPY (¥)", "JPY"),
            ("DZD (DA)", "DZD"),
            ("CAD ($)", "CAD"),
            ("AUD ($)", "AUD"),
            ("CHF (Fr)", "CHF"),
        ],
        value="USD",
        id="currency",
    ),
)


class PyCentsLocaleApp(App):
    """A Textual TUI showcasing PyCents local formatting."""

    CSS = """
    Screen {
        background: $surface-darken-2;
        align: center middle;
    }
    #main-panel {
        width: 95;
        height: auto;
        max-height: 100%;
        border: heavy $accent;
        background: $panel;
        padding: 1 2;
    }
    .row {
        height: auto;
        margin-bottom: 1;
    }
    .col {
        width: 1fr;
        height: auto;
        margin-right: 1;
    }
    Label {
        height: 1;
        text-style: bold;
        color: $secondary;
    }
    Input {
        height: 3;
        margin-bottom: 1;
    }
    Checkbox {
        height: 3;
        background: $boost;
        width: auto;
    }
    #result-box {
        height: 3;
        content-align: center middle;
        background: $boost;
        color: $success;
        text-style: bold;
        margin-top: 0;
        border: double $success;
    }
    #fmtspec {
        height: 3;
        content-align: center middle;
        background: $boost;
        color: $success;
        text-style: bold;
        margin-top: 0;
        border: double $success;
    }
    #error-box {
        height: 3;
        color: $error;
        text-style: bold;
        content-align: center middle;
        margin-top: 1;
    }

    .compact {

    }
    #stepper {
        display: none;
    }
    #stepper > Label {
        width: 100%;
        text-align: left;
    }
    #stepper > NumberSpinner {
        width: 100%;
    }
    .compact #stepper {
        display: block;
    }
    """

    BINDINGS = [
        ("d", "toggle_dark_mode", "Toggle Dark Mode"),
    ]

    def action_toggle_dark_mode(self) -> None:
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )

    def compose(self) -> ComposeResult:
        yield Header()

        with Vertical(id="main-panel"):
            yield Label("💸 Money Amount (Major Units):")
            yield Input(value="-1234567.89", placeholder="e.g., -1234.56", id="amount")

            with Horizontal(classes="row"):
                yield locales
                yield currencies

            with Horizontal(classes="row"):
                yield LabeledField(
                    "🎨 Display Mode:",
                    Select(
                        [
                            ("Symbol ($)", "symbol"),
                            ("ISO Code (USD)", "iso"),
                            ("Name (US Dollar)", "name"),
                            ("Hidden (None)", "hidden"),
                        ],
                        value="symbol",
                        id="display",
                    ),
                )

                with Vertical(classes="col"):
                    yield Label("⚙️ Format Type:")
                    with RadioSet(id="format_type"):
                        yield RadioButton("Standard", id="fmt_standard", value=True)
                        yield RadioButton("Accounting", id="fmt_accounting")
                        yield RadioButton("Compact", id="fmt_compact")

                with Vertical(classes="col", id="stepper"):
                    yield Label("🎯 Precision:")
                    yield NumberSpinner(1, id="spinner")

            with Horizontal(classes="row"):
                yield Checkbox("✂️ Trim Zeros", id="trim-zeros", value=False)
                yield Checkbox("🔢 Group Separator", id="group-sep", value=True)

            with Horizontal(classes="row"):
                yield LabeledField(
                    "🧾 Format Specification", Static('f"{amount}"', id="fmtspec")
                )
                yield LabeledField(
                    "🖥️ Output", Static("Initializing...", id="result-box")
                )
            yield Static("", id="error-box")

        yield Footer()

    def on_mount(self) -> None:
        """Trigger an initial render when the app starts."""
        self.update_formatting()

    def _get_select_val(self, selector: str, default: str) -> str:
        val = self.query_one(selector, Select).value
        return val if isinstance(val, str) else default

    def _build_fmt_spec(
        self,
        display: str,
        compact: bool,
        accounting: bool,
        precision: int | None = None,
        group_separator: bool = True,
        trim_zeroes: bool = False,
    ) -> str:
        _display_map = {"symbol": "", "iso": "i", "name": "n", "hidden": "h"}
        display = _display_map[display]
        if compact:
            fmt = "c"
        elif accounting:
            fmt = "a"
        else:
            fmt = ""
        if compact:
            prec = f".{precision}"
        else:
            prec = ""
        ungroup = "u" if not group_separator else ""
        trim = "~" if trim_zeroes else ""

        spec = f"{display}{prec}{fmt}{ungroup}{trim}"
        return f'f"{{{"amount"}:{spec}}}"'

    @on(Input.Changed, "#amount")
    @on(Select.Changed)
    @on(RadioSet.Changed)
    @on(Checkbox.Changed)
    @on(NumberSpinner.Changed)
    def update_formatting(self, event=None) -> None:
        amount_str = self.query_one("#amount", Input).value.strip()

        # Safely fetch all dropdown values
        locale_val = self._get_select_val("#locale", "en_US")
        currency_val = self._get_select_val("#currency", "USD")
        display_val = self._get_select_val("#display", "symbol")

        radio_set = self.query_one("#format_type", RadioSet)
        active_radio = radio_set.pressed_button
        active_id = active_radio.id if active_radio else "fmt_standard"

        compact_prec = 1
        if active_id == "fmt_compact":
            self.add_class("compact")
            compact_prec = self.query_one("#spinner", NumberSpinner).value
        else:
            self.remove_class("compact")

        trim = self.query_one("#trim-zeros", Checkbox).value
        grp_sep = self.query_one("#group-sep", Checkbox).value

        result_box = self.query_one("#result-box", Static)
        fmt_box = self.query_one("#fmtspec", Static)
        error_box = self.query_one("#error-box", Static)

        if not amount_str:
            result_box.update("")
            error_box.update("Enter a valid amount.")
            return

        try:
            money = Money.from_major(amount_str, currency_val)

            safe_display = cast(Literal["symbol", "iso", "name", "hidden"], display_val)

            with local_format(locale=locale_val) as fmt:
                fmt.display = safe_display
                fmt.compact = active_id == "fmt_compact"
                fmt.accounting = active_id == "fmt_accounting"
                fmt.compact_prec = compact_prec
                fmt.group_separator = grp_sep
                fmt.trim = trim

                formatted_string = f"{money}"

                # Build the format specification
                result = self._build_fmt_spec(
                    fmt.display,
                    fmt.compact,
                    fmt.accounting,
                    precision=fmt.compact_prec,
                    group_separator=fmt.group_separator,
                    trim_zeroes=fmt.trim,
                )

            fmt_box.update(result)
            result_box.update(formatted_string)
            error_box.update("")

        except Exception as err:
            result_box.update("")
            error_box.update(f"Error: {err}")


if __name__ == "__main__":
    app = PyCentsLocaleApp()
    app.run()
