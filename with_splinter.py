# https://github.com/cobrateam/splinter/

from selenium.webdriver.firefox.options import Options
from splinter import Browser
from firefox import find_firefox

import pytest

@pytest.fixture
def browser():
    options = Options()
    options.binary = find_firefox()

    with Browser('firefox', options=options) as browser:
        yield browser
        browser.quit()

def test_google(browser):
    browser.visit('https://google.com')
    browser.find_by_text("Ich stimme zu").click()
    
    browser.find_by_css('[title=Suche]').fill('Selenium')
    browser.find_by_css('[value="Google Suche"]').click()
    
    assert len(browser.find_by_css('.g')) >= 10
    assert browser.is_text_present("Selenium automates browsers")

observations = """
- nicely short
- searching is low level
- no explicit waiting. Nice!
"""
