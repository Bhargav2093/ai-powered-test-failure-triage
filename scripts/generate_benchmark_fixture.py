"""Generates a synthetic 500-failure JUnit XML fixture for the README's
metrics section.

Not a hand-wavy number: this builds ~20 distinct "true" root causes (the
kind of thing that actually breaks a suite - one flaky locator, one down
dependency, one real regression), each manifesting across a realistic
number of individual test cases with randomized-but-plausible noise
(different class names, line numbers, and asserted values), then writes
the whole thing as one JUnit-style testsuite. The triage pipeline is run
against this fixture for real (see scripts/run_benchmark.py) - the
reduction numbers in the README come from that real run, not from this
generator.

Deterministic: seeded RNG, so re-running this script reproduces the exact
same fixture and therefore the exact same downstream metrics.
"""

from __future__ import annotations

import random
from pathlib import Path
from xml.sax.saxutils import quoteattr

_SEED = 20260818
_TOTAL_FAILURES = 500

# Each root cause: (category_hint, class_name, test_name_prefix, exception_type,
# message_template, stack_template, weight). weight is relative share of the
# 500 total failures - some root causes are noisy (touch many tests), most
# are contained to a handful.
_ROOT_CAUSES = [
    # --- flaky (UI timing/locator signals) ---
    ("com.example.tests.LoginTests", "loginButtonClickable",
     "org.openqa.selenium.ElementClickInterceptedException",
     "element click intercepted: Element is not clickable at point ({x}, {y})",
     "at org.openqa.selenium.remote.RemoteWebElement.click(RemoteWebElement.java:{line})\n"
     "\tat com.example.pages.LoginPage.clickLogin(LoginPage.java:{line2})", 42),
    ("com.example.tests.CheckoutTests", "submitButtonStaleAfterReload",
     "org.openqa.selenium.StaleElementReferenceException",
     "stale element reference: element is not attached to the page document",
     "at org.openqa.selenium.remote.RemoteWebElement.click(RemoteWebElement.java:{line})\n"
     "\tat com.example.pages.CheckoutPage.clickSubmit(CheckoutPage.java:{line2})", 38),
    ("com.example.tests.SearchTests", "resultsGridRendersInTime",
     "org.openqa.selenium.TimeoutException",
     "Expected condition failed: waiting for element to be visible (tried for {timeout} "
     "second(s) with 500 MILLISECONDS interval)",
     "at org.openqa.selenium.support.ui.WebDriverWait.until(WebDriverWait.java:{line})\n"
     "\tat com.example.pages.SearchResultsPage.waitForGrid(SearchResultsPage.java:{line2})", 35),
    ("com.example.tests.NavTests", "menuItemNotInteractable",
     "org.openqa.selenium.ElementNotInteractableException",
     "element not interactable",
     "at org.openqa.selenium.remote.RemoteWebElement.click(RemoteWebElement.java:{line})\n"
     "\tat com.example.pages.NavBar.selectMenuItem(NavBar.java:{line2})", 21),
    ("com.example.tests.ProfileTests", "avatarUploadWidgetMissing",
     "org.openqa.selenium.NoSuchElementException",
     "no such element: Unable to locate element: {{\"method\":\"css selector\","
     "\"selector\":\".avatar-upload\"}}",
     "at org.openqa.selenium.remote.RemoteWebDriver.findElement(RemoteWebDriver.java:{line})\n"
     "\tat com.example.pages.ProfilePage.uploadAvatar(ProfilePage.java:{line2})", 18),
    # --- infra (down/unreachable dependency signals) ---
    ("com.example.tests.ApiHealthTests", "pingInternalService",
     "java.net.ConnectException",
     "Connection refused: connect",
     "at java.base/sun.nio.ch.Net.pollConnect(Native Method)\n"
     "\tat com.example.api.InternalServiceClient.ping(InternalServiceClient.java:{line})", 33),
    ("com.example.tests.PaymentGatewayTests", "authorizeCardTimesOut",
     "java.net.SocketTimeoutException",
     "Read timed out",
     "at java.base/sun.net.NetworkClient.doRead(NetworkClient.java:{line})\n"
     "\tat com.example.api.PaymentGatewayClient.authorize(PaymentGatewayClient.java:{line2})", 27),
    ("com.example.tests.NotificationTests", "smtpRelayUnresolvable",
     "java.net.UnknownHostException",
     "smtp.internal.example.local: Name or service not known",
     "at java.base/java.net.Inet6AddressImpl.lookupAllHostAddr(Inet6AddressImpl.java:{line})\n"
     "\tat com.example.mail.SmtpRelayClient.connect(SmtpRelayClient.java:{line2})", 19),
    ("com.example.tests.SearchIndexTests", "indexServiceNoResponse",
     "org.apache.http.NoHttpResponseException",
     "internal-search-01:9200 failed to respond",
     "at org.apache.http.impl.conn.DefaultHttpResponseParser.parseHead"
     "(DefaultHttpResponseParser.java:{line})\n"
     "\tat com.example.search.SearchIndexClient.query(SearchIndexClient.java:{line2})", 14),
    # --- regression (real assertion failures, one true positive per shape) ---
    ("com.example.tests.CartTests", "cartTotalMatchesLineItems",
     "java.lang.AssertionError",
     "expected [{expected}] but found [{actual}]",
     "at org.testng.Assert.fail(Assert.java:{line})\n"
     "\tat org.testng.Assert.assertEquals(Assert.java:{line2})\n"
     "\tat com.example.tests.CartTests.cartTotalMatchesLineItems(CartTests.java:{line3})", 31),
    ("com.example.tests.DiscountTests", "loyaltyDiscountAppliedTwice",
     "java.lang.AssertionError",
     "expected discount total [{expected}] but was [{actual}]",
     "at org.testng.Assert.fail(Assert.java:{line})\n"
     "\tat org.testng.Assert.assertEquals(Assert.java:{line2})\n"
     "\tat com.example.tests.DiscountTests.loyaltyDiscountAppliedTwice(DiscountTests.java:{line3})",
     24),
    ("com.example.tests.InventoryTests", "reservedStockNotDecremented",
     "java.lang.AssertionError",
     "expected available stock [{expected}] but was [{actual}]",
     "at org.testng.Assert.fail(Assert.java:{line})\n"
     "\tat org.testng.Assert.assertEquals(Assert.java:{line2})\n"
     "\tat com.example.tests.InventoryTests.reservedStockNotDecremented(InventoryTests.java:{line3})",
     22),
    ("com.example.tests.ShippingTests", "expressRateMiscalculated",
     "java.lang.AssertionError",
     "expected shipping rate [{expected}] but was [{actual}]",
     "at org.testng.Assert.fail(Assert.java:{line})\n"
     "\tat org.testng.Assert.assertEquals(Assert.java:{line2})\n"
     "\tat com.example.tests.ShippingTests.expressRateMiscalculated(ShippingTests.java:{line3})", 17),
    ("com.example.tests.RefundTests", "partialRefundLeavesOrphanCredit",
     "java.lang.AssertionError",
     "expected refunded amount [{expected}] but was [{actual}]",
     "at org.testng.Assert.fail(Assert.java:{line})\n"
     "\tat org.testng.Assert.assertEquals(Assert.java:{line2})\n"
     "\tat com.example.tests.RefundTests.partialRefundLeavesOrphanCredit(RefundTests.java:{line3})",
     15),
    ("com.example.tests.TaxTests", "regionalTaxRateOffByOnePercent",
     "java.lang.AssertionError",
     "expected tax amount [{expected}] but was [{actual}]",
     "at org.testng.Assert.fail(Assert.java:{line})\n"
     "\tat org.testng.Assert.assertEquals(Assert.java:{line2})\n"
     "\tat com.example.tests.TaxTests.regionalTaxRateOffByOnePercent(TaxTests.java:{line3})", 13),
    ("com.example.tests.WishlistTests", "sharedWishlistDuplicatesItems",
     "java.lang.AssertionError",
     "expected item count [{expected}] but was [{actual}]",
     "at org.testng.Assert.fail(Assert.java:{line})\n"
     "\tat org.testng.Assert.assertEquals(Assert.java:{line2})\n"
     "\tat com.example.tests.WishlistTests.sharedWishlistDuplicatesItems(WishlistTests.java:{line3})",
     11),
    ("com.example.tests.CouponTests", "expiredCouponStillRedeemable",
     "java.lang.AssertionError",
     "expected redemption result [{expected}] but was [{actual}]",
     "at org.testng.Assert.fail(Assert.java:{line})\n"
     "\tat org.testng.Assert.assertEquals(Assert.java:{line2})\n"
     "\tat com.example.tests.CouponTests.expiredCouponStillRedeemable(CouponTests.java:{line3})", 9),
    ("com.example.tests.WarehouseTests", "transferOrderQuantityRounded",
     "java.lang.AssertionError",
     "expected transfer quantity [{expected}] but was [{actual}]",
     "at org.testng.Assert.fail(Assert.java:{line})\n"
     "\tat org.testng.Assert.assertEquals(Assert.java:{line2})\n"
     "\tat com.example.tests.WarehouseTests.transferOrderQuantityRounded(WarehouseTests.java:{line3})",
     10),
]


def _noisy(rng: random.Random, template: str) -> str:
    return template.format(
        x=rng.randint(40, 900),
        y=rng.randint(40, 900),
        line=rng.randint(20, 400),
        line2=rng.randint(20, 400),
        line3=rng.randint(20, 400),
        timeout=rng.choice([5, 10, 15, 20, 30]),
        expected=f"{rng.uniform(5, 500):.2f}",
        actual=f"{rng.uniform(5, 500):.2f}",
    )


def generate(total: int = _TOTAL_FAILURES, seed: int = _SEED) -> str:
    rng = random.Random(seed)

    total_weight = sum(rc[-1] for rc in _ROOT_CAUSES)
    counts = []
    for *_rest, weight in _ROOT_CAUSES:
        counts.append(max(1, round(total * weight / total_weight)))
    # Rounding drift: pad/trim the largest bucket so the total matches exactly.
    drift = total - sum(counts)
    counts[counts.index(max(counts))] += drift

    testcases = []
    case_index = 0
    for (class_name, test_prefix, exc_type, msg_tmpl, trace_tmpl, _weight), count in zip(
        _ROOT_CAUSES, counts
    ):
        for i in range(count):
            case_index += 1
            message = _noisy(rng, msg_tmpl)
            trace = f"{exc_type}: {message}\n\t{_noisy(rng, trace_tmpl)}"
            test_name = f"{test_prefix}_{i:03d}"
            duration = round(rng.uniform(0.2, 6.0), 3)
            testcases.append(
                f'  <testcase classname="{class_name}" name={quoteattr(test_name)} '
                f'time="{duration}">\n'
                f"    <failure message={quoteattr(message)} type=\"{exc_type}\">\n"
                f"      <![CDATA[{trace}]]>\n"
                f"    </failure>\n"
                f"  </testcase>"
            )

    header = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<!-- Synthetic benchmark fixture: generated by scripts/generate_benchmark_fixture.py.\n"
        f"     {len(_ROOT_CAUSES)} distinct root causes across {case_index} individual failing\n"
        "     test cases, with per-instance noise (line numbers, coordinates, asserted values)\n"
        "     so no two failures are byte-identical - closer to what a real noisy CI run looks\n"
        "     like than a hand-written fixture would be. Seeded RNG: re-running this script\n"
        "     reproduces this exact file. -->\n"
        f'<testsuite hostname="synthetic-benchmark-runner" failures="{case_index}" '
        f'tests="{case_index}" name="com.example.tests.BenchmarkSuite" time="0" errors="0" '
        f'timestamp="2026-08-18T00:00:00 UTC" skipped="0">\n'
    )
    return header + "\n".join(testcases) + "\n</testsuite>\n"


if __name__ == "__main__":
    output_path = Path(__file__).resolve().parent.parent / "samples" / "benchmark" / "synthetic_500_failures.xml"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(generate(), encoding="utf-8")
    print(f"Wrote {output_path}")
