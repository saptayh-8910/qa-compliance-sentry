from playwright.sync_api import Page, expect


class CartPage:
    def __init__(self, page: Page) -> None:
        self.page = page

    def assert_item_present(self, name: str) -> None:
        expect(self.page.locator(".inventory_item_name", has_text=name)).to_be_visible()

    def proceed_to_checkout(self) -> None:
        self.page.locator("#checkout").click()
