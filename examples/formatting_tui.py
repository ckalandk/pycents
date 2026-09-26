from pycents import Money, RoundingMode, formatting

#######################################
# Using the default backend formatter #
#######################################

mny = Money.from_major(29, "USD")
print(f"{mny}")  # USD 29.00
print(f"{-mny}")  # -USD 29.00

# Display using currency name
# ---------------------------
print(f"{mny:n}")  # 29.00 US Dollar

# Display in accounting format
# ----------------------------
print(f"{-mny:a}")  # (USD 29.00)

# Display using compact notation
# ------------------------------
big_mny = Money.from_major("29880124567", "USD")
print(f"{big_mny:c}")  # USD 2.9B

# By default all backend formatters display one decimal
# in compact notation, you can control the number of decimals:
print(f"{big_mny:.4c}")  # USD 29.8801B

# The default rounding mode used in compact notation is half-even

# Changing the rounding mode globally
# -----------------------------------
formatting.get_formatter().configure(rounding=RoundingMode.DOWN)
print(f"{big_mny:c}")  # USD 29.8B

formatting.get_formatter().configure(rounding=RoundingMode.UP)
print(f"{big_mny:c}")  # USD 29.9B

# Changing the rounding mode for specific block of code
# -----------------------------------------------------

# Configure a rounding mode globally to see the effect of
# local_format() context
formatting.get_formatter().configure(rounding=RoundingMode.DOWN)

with formatting.local_format() as fmt:
    fmt.rounding = RoundingMode.UP
    print(f"{big_mny:c}")  # USD 29.9B

# Rounding Mode will be restored to it's default: round down
print(f"{big_mny:c}")  # USD 29.8B

# By default, decimals are displayed up to the
# currency's minor units including the non-significant zeros.
# This behavior may be ok for fiat currencies
# but when working with crypto-currencies it might
# be overwhelming to see numbers: BTC 29.99000000
# The format field ~ can be used to trim insignificant zeros

bitcoins = Money.from_major("29.99", "BTC")
print(f"{bitcoins}")  # BTC 29.99000000
print(f"{bitcoins:~}")  # BTC 29.99

# Combining different display options
# -----------------------------------

big_mny = Money.from_major("-29880124567", "USD")

# Use compact notation with three decimals, display
# negative amounts in accounting format and trim
# non significant zeros
print(f"{big_mny:.3ca~}")  # (USD 29.88B)

# Limitation: The standard formatter cannot display
# monetary amounts using currency's symbol


#########################################
# Using a local aware backend formatter #
#########################################

# PyCents support both icu and babel, hereby will use
# Babel.

# Choosing a backend formatter
# ----------------------------

formatting.use_backend("babel")  # Other options are 'std' and 'icu'

# By default, the local host machine will be used,
# You can though request another locale via:
formatting.basicConfig(locale="en_US")
# Note: Choosing a locale must be done after selecting a local-aware
# formatter like babel or icu.

# Now we are ready to format money

# Default formatting
# ---------------
mny = Money.from_major(29, "USD")
print(f"{mny}")  # $29.00

# Formatting using iso code
# -------------------------
print(f"{mny:i}")  # USD 29.00

# Formatting using currency name
# ------------------------------
print(f"{mny:n}")  # 29 US dollars
