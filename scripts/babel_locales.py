import re
from typing import Any

import icu as _icu
from babel.core import Locale, UnknownLocaleError

icu: Any = _icu

target_file = "tests/test_babel_formatter.py"


def load_locales() -> list[str]:
    locales = icu.Locale.getAvailableLocales()
    babel_locales = []
    for locale in locales:
        try:
            loc = Locale.parse(str(locale))
            babel_locales.append(str(loc))
        except UnknownLocaleError:
            continue
    babel_locales.sort()
    return babel_locales


def update_test_file():
    formatted_locales = load_locales()
    formatted_list = (
        "[\n" + ",\n".join(f'    "{loc}"' for loc in formatted_locales) + "\n]"
    )

    with open(target_file, encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(r"^(\s*)locales\s*=\s*\[[\s\S]*?\]", re.MULTILINE)

    if not pattern.search(content):
        print("Error: Could locate 'locales = [...]' block in the test file.")
        return

    replacement = r"\1locales = " + formatted_list
    new_content = pattern.sub(replacement, content)

    with open(target_file, "w", encoding="utf-8") as f:
        f.write(new_content)


if __name__ == "__main__":
    update_test_file()
