from __future__ import annotations

import pytest
from playwright.sync_api import Page

from tests.e2e.pages.cart_page import CartPage
from tests.e2e.pages.checkout_page import CheckoutPage
from tests.e2e.pages.inventory_page import InventoryPage
from tests.e2e.pages.login_page import LoginPage

pytestmark = pytest.mark.external


@pytest.mark.smoke
def test_checkout_happy_path(
    page: Page,
    sauce_base_url: str,
    sauce_username: str,
    sauce_password: str,
) -> None:
    login = LoginPage(page, sauce_base_url)
    login.open()
    login.login(sauce_username, sauce_password)
    login.assert_logged_in()

    inventory = InventoryPage(page)
    inventory.assert_on_inventory()
    inventory.add_item_by_name("Sauce Labs Backpack")
    assert inventory.cart_badge_count() == 1

    inventory.open_cart()
    cart = CartPage(page)
    cart.assert_item_present("Sauce Labs Backpack")
    cart.proceed_to_checkout()

    checkout = CheckoutPage(page)
    checkout.fill_information("Ada", "Lovelace", "12345")
    checkout.continue_checkout()
    checkout.finish_order()
    checkout.assert_order_complete()


@pytest.mark.regression
@pytest.mark.parametrize(
    "product_name",
    ["Sauce Labs Backpack", "Sauce Labs Bolt T-Shirt"],
)
def test_add_multiple_products_to_cart(
    page: Page,
    sauce_base_url: str,
    sauce_username: str,
    sauce_password: str,
    product_name: str,
) -> None:
    login = LoginPage(page, sauce_base_url)
    login.open()
    login.login(sauce_username, sauce_password)

    inventory = InventoryPage(page)
    inventory.add_item_by_name(product_name)
    assert inventory.cart_badge_count() == 1
