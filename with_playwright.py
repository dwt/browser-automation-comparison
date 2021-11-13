# https://github.com/Microsoft/playwright-python
# Does not seem to use selenium? Does not seem to use Webdriver, uses special Browser-Builds instead?

from playwright.sync_api import sync_playwright

import pytest

HEADLESS = True
# HEADLESS = False

@pytest.fixture
def page():
    with sync_playwright() as playwright:
        browser = playwright.firefox.launch(headless=HEADLESS)
        yield browser.new_page()
        browser.close()

def test_google(page):
    page.goto('https://google.com/')
    page.click('text=Ich stimme zu')
    page.fill('css=[title=Suche]', 'Playwright')  # does not give focus!
    page.click('css=[value="Google Suche"]:visible')  # Not automatically choosing visible elment
    page.wait_for_load_state("networkidle")  # wtf is this neccessary?
    assert len(page.query_selector_all('.g')) >= 10
    content = page.text_content('css=.g:first-child')
    assert 'Playwright enables reliable end-to-end testing for modern web apps' in content

observations = """
- Quite low level
- Explicit waiting. Ugh
- Self-Downloads browsers, nicely self contained
- Not based on Selenium / Webdriver
"""
