from playwright.sync_api import Page, expect


class InventoryPage:
    def __init__(self, page: Page) -> None:
        self.page = page

    def add_item_by_name(self, name: str) -> None:
        item = self.page.locator(".inventory_item").filter(has_text=name)
        item.locator("button").filter(has_text="Add to cart").click()

    def open_cart(self) -> None:
        self.page.locator(".shopping_cart_link").click()

    def assert_on_inventory(self) -> None:
        expect(self.page.locator(".title")).to_have_text("Products")

    def cart_badge_count(self) -> int:
        badge = self.page.locator(".shopping_cart_badge")
        if badge.count() == 0:
            return 0
        return int(badge.inner_text())
