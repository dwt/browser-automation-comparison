# https://www.selenium.dev/selenium/docs/api/py/

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

from firefox import find_firefox

import pytest

HEADLESS = True
HEADLESS = False

WAIT = 2

@pytest.fixture
def browser():
    options = webdriver.firefox.options.Options()
    options.headless = HEADLESS
    browser = webdriver.Firefox(options=options, firefox_binary=find_firefox())
    browser.implicitly_wait(WAIT)
    yield browser
    browser.quit()

def test_google(browser):
    """
    - can auto wait
    - increadibly basic selector support, no support for compound stuff (class + text) out of the box
    - quite verbose…
    """
    
    browser.get('http://google.com/')
    assert 'Google' in browser.title
    
    browser.find_element(By.XPATH, '//button[normalize-space()="Ich stimme zu"]').click()
    search_field = browser.find_element(By.CSS_SELECTOR, '[title="Suche"]')
    search_field.send_keys('Selenium' + Keys.RETURN)
    
    assert len(browser.find_elements(By.CSS_SELECTOR, '.g')) >= 10
    
    first = browser.find_element(By.CSS_SELECTOR, '.g') # first, note missing 's'
    assert 'Selenium automates browsers' in first.text

def until(driver, condition, wait=WAIT):
    driver.implicitly_wait(0)
    try:
        return WebDriverWait(driver, wait).until(condition)
    finally:
        driver.implicitly_wait(WAIT)

class NestedSearch(object):
    
    def __init__(self, *locators):
        self.locators = locators
    
    def __call__(self, driver):
        current = driver
        for locator in self.locators:
            current = current.find_element(*locator)
        return current

def test_nested_select_with_retry(browser, flask_uri):
    """
    - nested searching sucks, but is possible with some helpers
    """
    browser.get(flask_uri + '/dynamic_disclose')
    browser.find_element(By.XPATH, '//*[text()="Trigger"]').click()
    inner = until(browser, NestedSearch(
        (By.ID, 'outer'),
        (By.XPATH, './/*[@id="inner"][contains(text(), "fnord")]')
    ))
    assert 'fnord' in inner.text

def by_label(label_text):
    # could use xpath library from capybara
    return (By.XPATH, 
        f'//input[@id = //label[contains(string(.), "{label_text}")]/@for]'
        f' | //label[contains(string(.), "{label_text}")]//input'
    )

def test_fill_form(browser, flask_uri):
    """
    - Locating elements by their label is... hard.
    - Can be done with xpath of course, but at that point I'm actually rebuilding capybaras
    """
    browser.get(flask_uri + '/form')
    browser.find_element(*by_label("First name")).send_keys('Martin')
    browser.find_element(*by_label("Last name")).send_keys('Häcker')
    browser.find_element(By.CSS_SELECTOR, '[placeholder="your@email"]').send_keys('foo@bar.org')
    
    assert 'Martin' == browser.find_element_by_id('first_name').get_attribute('value')
    assert 'Häcker' == browser.find_element_by_id('last_name').get_attribute('value')
    assert 'foo@bar.org' == browser.find_element_by_id('email').get_attribute('value')
