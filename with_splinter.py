# https://github.com/cobrateam/splinter/

from selenium.webdriver.firefox.options import Options
from splinter import Browser
from firefox import find_firefox

import pytest

HEADLESS = True
HEADLESS = False

@pytest.fixture
def browser():
    options = Options()
    options.binary = find_firefox()
    options.headless = HEADLESS

    with Browser('firefox', options=options) as browser:
        yield browser
        browser.quit()

def test_google(browser):
    """
    - nicely short
    - searching is low level
    - no explicit waiting. Nice!
    """
    
    browser.visit('https://google.com')
    browser.find_by_text("Ich stimme zu").click()
    
    browser.find_by_css('[title=Suche]').fill('Selenium')
    browser.find_by_css('[value="Google Suche"]').click()
    
    assert len(browser.find_by_css('.g')) >= 10
    assert browser.is_text_present("Selenium automates browsers")

def test_nested_select_with_retry(browser, flask_uri):
    """
    - can do nested searches
    - but not mixed with matchers, those can only be done on browser
    - There seems to be no API suppport to express complex matchers (i.e. this class AND that text)
    - Of course can write them as xpath if I really need to...
    """
    browser.visit(flask_uri + '/dynamic_disclose')
    browser.find_by_text("Trigger").click()
    browser.is_text_present('fnord')
    inner = browser.find_by_css('#outer').find_by_css('#inner')
    assert 'fnord' in inner.text
