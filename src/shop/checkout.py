"""Order checkout.

The rules live in `src/shop/specs/checkout.md` - read it first.
The signatures below are final, the bodies are yours.
Do not change the constants: the tests rely on them.
"""

from shop.money import percent_of

PROMO_CODES = {"WELCOME10": 10, "SUMMER15": 15, "VIP35": 35}
SUPPORTED_CITIES = ("msk", "spb")
MAX_DISCOUNT_PERCENT = 30
VAT_PERCENT = 20
SHIPPING_KOPEKS = 49_000
FREE_DELIVERY_FROM_KOPEKS = 500_000
TIER_DISCOUNTS = ((10, 5), (25, 10), (50, 15))
REQUIRED_LINE_KEYS = ("sku", "qty", "unit_price_kopecks")


def _parses_as_int(text: str) -> bool:
    """Return True when warehouse text survives int() without raising.

    The leading sign is cut off so a signed value still counts as a number -
    its sign belongs to the range rules - and the ascii guard blocks unicode
    digits that int() rejects. Raising is forbidden in this project.
    """
    unsigned = text.strip()
    if unsigned[:1] in ("+", "-"):
        unsigned = unsigned[1:]
    return unsigned.isascii() and unsigned.isdigit()


def _validate_line(position: int, item: dict[str, str]) -> str | None:
    """Return why one order line is invalid (spec 3 rules 2-7), or None."""
    # Spec 3 rule 2: without an article code the goods cannot be identified.
    # `.get` instead of `[]` keeps a missing key from crashing before rule 3 exists.
    if not item.get("sku"):
        return f"Line {position} has an empty sku."
    # Spec 3 rule 3: a missing key means the export is broken and the line
    # cannot be priced, so the whole order is refused.
    for key in REQUIRED_LINE_KEYS:
        if key not in item:
            return f"Line {position} is missing key {key}."
    # Spec 3 rule 4: qty arrives as warehouse text and only text that int()
    # parses may be priced; the check stands in for int() itself.
    if not _parses_as_int(item["qty"]):
        return f"Line {position} has a non-numeric qty."
    # Spec 3 rule 5: nothing to sell when the quantity is zero or negative.
    if int(item["qty"]) <= 0:
        return f"Line {position} has a qty that is not greater than zero."
    # Spec 3 rule 6: the price is warehouse text too, and only text int()
    # parses may enter the money math.
    if not _parses_as_int(item["unit_price_kopecks"]):
        return f"Line {position} has a non-numeric unit price."
    # Spec 3 rule 7: a negative price would pay the customer to shop here.
    if int(item["unit_price_kopecks"]) < 0:
        return f"Line {position} has a negative unit price."
    return None


def validate_order(
    lines: list[dict[str, str]],
    promo_code: str = "",
    shipping_city: str = "",
) -> str | None:
    """Return a human readable reason why the order is invalid, or None if it is fine."""
    # Spec 3 rule 1: an empty basket has nothing to price, so refuse it up front.
    if not lines:
        return "Order has no lines."
    seen_skus: set[str] = set()
    for position, item in enumerate(lines, start=1):
        reason = _validate_line(position, item)
        if reason is not None:
            return reason
        # Spec 3 rule 8: an article may appear only once - two lines sharing one
        # sku would double-count the goods, so the sku is remembered per order.
        if item["sku"] in seen_skus:
            return f"Line {position} repeats sku {item['sku']}."
        seen_skus.add(item["sku"])
    # Spec 3 rule 9: an unknown promo code is a promise of a discount we cannot honour.
    if promo_code and promo_code not in PROMO_CODES:
        return f"Unknown promo code {promo_code}."
    # Spec 3 rule 10: we only deliver where we have partners; an empty city is pickup.
    if shipping_city and shipping_city not in SUPPORTED_CITIES:
        return f"Unsupported shipping city {shipping_city}."
    return None


def calculate_order_total(
    lines: list[dict[str, str]],
    promo_code: str = "",
    shipping_city: str = "",
) -> int | None:
    """Return the order total in kopecks, or None if the order is invalid."""
    # Spec 4: a rejected order has no total, only None.
    if validate_order(lines, promo_code, shipping_city) is not None:
        return None
    # The smoke test prices one plain line, so only steps 1 and 9-10 existed
    # until the tier test arrived; promo and delivery come with their own tests.
    subtotal = sum(int(item["qty"]) * int(item["unit_price_kopecks"]) for item in lines)
    units = sum(int(item["qty"]) for item in lines)
    # Spec 4 step 2: the biggest threshold that fits wins. TIER_DISCOUNTS is
    # ordered ascending, so the last match is the largest matching tier.
    tier_percent = 0
    for threshold, percent in TIER_DISCOUNTS:
        if units >= threshold:
            tier_percent = percent
    # Spec 4 steps 3-4: the promo code brings its own percent, and the bigger
    # of the two wins - discounts never stack.
    promo_percent = PROMO_CODES.get(promo_code, 0)
    discount_percent = max(tier_percent, promo_percent)
    # Spec 4 step 5: no percent may exceed the cap, whatever its source.
    discount_percent = min(discount_percent, MAX_DISCOUNT_PERCENT)
    # Steps 5-6: one whole-percent discount, no floats anywhere.
    discounted_subtotal = subtotal - percent_of(subtotal, discount_percent)
    # Spec 4 step 7: delivery is a flat fee for a city order that stays below
    # the free threshold - and the threshold is judged after the discount.
    delivery = (
        SHIPPING_KOPEKS if shipping_city and discounted_subtotal < FREE_DELIVERY_FROM_KOPEKS else 0
    )
    # Steps 8-10: VAT applies to the base, delivery included.
    base = discounted_subtotal + delivery
    vat = percent_of(base, VAT_PERCENT)
    return base + vat
