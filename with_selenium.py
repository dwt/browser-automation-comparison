# https://www.selenium.dev/selenium/docs/api/py/

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from firefox import find_firefox

import pytest

@pytest.fixture
def browser():
    browser = webdriver.Firefox(firefox_binary=find_firefox())
    browser.implicitly_wait(10)
    yield browser
    browser.quit()

def test_google(browser):
    browser.get('http://google.com/')
    assert 'Google' in browser.title
    
    browser.find_element(By.XPATH, '//button[normalize-space()="Ich stimme zu"]').click()
    search_field = browser.find_element(By.CSS_SELECTOR, '[title="Suche"]')
    search_field.send_keys('Selenium' + Keys.RETURN)
    
    assert len(browser.find_elements(By.CSS_SELECTOR, '.g')) >= 10
    
    first = browser.find_element(By.CSS_SELECTOR, '.g') # first, note missing 's'
    assert 'Selenium automates browsers' in first.text

observations = """
- can auto wait
- increadibly basic selector support, no support for compound stuff (class + text) out of the box
- quite verbose…
"""
