from playwright.sync_api import Page, expect


class LoginPage:
    def __init__(self, page: Page, base_url: str) -> None:
        self.page = page
        self.base_url = base_url.rstrip("/")

    def open(self) -> None:
        self.page.goto(self.base_url)

    def login(self, username: str, password: str) -> None:
        self.page.locator("#user-name").fill(username)
        self.page.locator("#password").fill(password)
        self.page.locator("#login-button").click()

    def assert_logged_in(self) -> None:
        expect(self.page).to_have_url(f"{self.base_url}/inventory.html")
