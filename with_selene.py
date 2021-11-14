# https://github.com/yashaka/selene

from selene import by, be, have
from selene.core.condition import Condition
from firefox import find_firefox

from selenium.webdriver.firefox.options import Options

from selenium.webdriver import Firefox

import pytest

HEADLESS = True
# HEADLESS = False

@pytest.fixture
def browser():
    from selene.support.shared import browser
    
    options = Options()
    options.binary = find_firefox()
    options.headless = HEADLESS
    
    browser.config.set_driver = lambda: Firefox(options=options)
    browser.config.browser_name = 'firefox'
    # auto wait timeout
    browser.config.timeout = 2
    
    yield browser

def test_google(browser):
    """
    - lots of warnings raised?
    - fluid api looks nice
    - in active development
    - fluid inline assertions. Nice!
    """
    
    browser.open('https://google.com/')
    browser.element(by.text('Ich stimme zu')).click()
    browser.element(by.css('[title=Suche]')).should(be.blank) \
        .type('selenium').press_enter()
    
    browser.all('.g').should(have.size_greater_than_or_equal(10)) \
        .first.should(have.text('Selenium automates browsers'))

def test_nested_select_with_retry(browser, flask_uri):
    """
    - nested search writes itself very nicely
    - not sure if that is the right way to express compund search queries
    """
    browser.open(flask_uri + '/dynamic_disclose')
    browser.element(by.text('Trigger')).click()
    browser.element(by.css('#outer')).element(by.css('#inner')).should(have.text('fnord'))
