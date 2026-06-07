from playwright.sync_api import Page, expect


class CheckoutPage:
    def __init__(self, page: Page) -> None:
        self.page = page

    def fill_information(self, first: str, last: str, zip_code: str) -> None:
        self.page.locator("#first-name").fill(first)
        self.page.locator("#last-name").fill(last)
        self.page.locator("#postal-code").fill(zip_code)

    def continue_checkout(self) -> None:
        self.page.locator("#continue").click()

    def finish_order(self) -> None:
        self.page.locator("#finish").click()

    def assert_order_complete(self) -> None:
        expect(self.page.locator(".complete-header")).to_have_text(
            "Thank you for your order!"
        )
