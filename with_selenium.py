# https://www.selenium.dev/selenium/docs/api/py/

from contextlib import contextmanager

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.alert import Alert

from conftest import find_firefox, assert_is_png, add_auth_to_uri

import pytest

HEADLESS = True
HEADLESS = False

WAIT = 2

@pytest.fixture
def browser():
    options = webdriver.firefox.options.Options()
    options.headless = HEADLESS
    # required or marionette will not allow them
    options.set_preference("dom.disable_beforeunload", False)
    # required to allow username and password in url for basic auth
    # http://kb.mozillazine.org/Network.http.phishy-userpass-length
    # currently set automatically
    # options.set_preference('network.http.phishy-userpass-length', 255)

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

def test_fallback_to_selenium_and_js(browser, flask_uri):
    """
    - selection by js is possible but cumbersome
    """
    browser.get(flask_uri + '/form')
    element = browser.find_element(*by_label("First name"))
    parent_element = browser.execute_script('return arguments[0].parentElement', element)
    assert parent_element.tag_name == 'form'

def test_select_by_different_criteria(browser, flask_uri, xpath):
    """
    - not much support to select by
    - can integrate xpath selector libraries fairly easily
    """
    browser.get(flask_uri + '/selector_playground')
    
    def assert_field(*args, **kwargs):
        assert browser.find_element(*args, **kwargs).get_attribute('value') == 'input_value'
    
    # simple criterias
    assert_field(By.CLASS_NAME, 'input_class')
    assert_field(By.CSS_SELECTOR, '#input_id')
    assert_field(By.ID, 'input_id')
    assert_field(By.NAME, 'input_name')
    assert_field(By.TAG_NAME, 'input')
    assert_field(By.XPATH, '//*[@placeholder="input_placeholder"]')
    # LINK_TEXT, PARTIAL_LINK_TEXT not applicable
    
    # Aria - no special support
    
    # Complex criteria, can be done with css or xpath
    assert_field(By.CSS_SELECTOR, '[placeholder=input_placeholder][name=input_name]')
    assert_field(By.XPATH, '//*[@placeholder="input_placeholder"][@name="input_name"]')
    
    # can integrate xpath libraries
    assert_field(By.XPATH, xpath.field('input_label'))

def test_debugging_support(browser, flask_uri, tmp_path):
    """
    - nothing special, nothign unexpected
    """
    browser.get(flask_uri + '/selector_playground')
    
    # get html of page
    assert '<label for' in browser.page_source
    # get html of a selection
    field = browser.find_element(By.XPATH, '//input')
    assert field.get_attribute('outerHTML').startswith('<input id=')
    
    
    # get screenshot of page
    path = tmp_path / 'full_screenshot.png'
    browser.save_screenshot(path.as_posix())
    assert_is_png(path)
    
    # getting at browser logs used to be an enableable capability
    # and then browser.get_log('browser'). But that was lost in the transition to webdriver
    # One can still somewhat get logs by instructing firefox to put them into the geckodriver.log
    # but...

def test_isolation(browser, flask_uri, ask_to_leave_script):
    """
    - no support for reset, just starts a new browser with a new profile
    - Effective, if brute force. Also really slow. :-/
    """

def test_dialogs(browser, flask_uri, ask_to_leave_script):
    """
    - surprisingly easy nice api to work with alerts
    """
    browser.get(flask_uri)
    # accepting or dismissing an anticipated alert ist simple
    browser.execute_script('alert("fnord")')
    browser.switch_to.alert.accept()
    
    # detect that an alert is currently being shown
    assert EC.alert_is_present()(browser) is False
    browser.execute_script('alert("fnord")')
    assert isinstance(EC.alert_is_present()(browser), Alert)
    browser.switch_to.alert.accept()
    
    # can work with leave alerts the same way
    browser.execute_script(ask_to_leave_script)
    element = browser.find_element(*by_label("input_label"))
    element.send_keys('fnord') # now page is changed
    browser.get(flask_uri)
    assert isinstance(EC.alert_is_present()(browser), Alert)
    browser.switch_to.alert.accept()
    assert EC.alert_is_present()(browser) is False

@contextmanager
def window(browser, new_indow_handle):
    current_window_handle = browser.current_window_handle
    browser.switch_to.window(new_indow_handle)
    yield
    browser.switch_to.window(current_window_handle)

def test_working_with_multiple_window(browser, flask_uri):
    """
    - Has the concept `driver.current_window`, and therefore 
      no real object to talk to a specific window.
    - can be worked around, but not so super nice
    """
    
    def set_value(selector, value):
        element = browser.find_element(*selector)
        element.clear()
        element.send_keys(value)
    
    first_window_handle = browser.current_window_handle
    browser.get(flask_uri)
    set_value(by_label("input_label"), 'first window')
    
    def window_handle_opened_by(a_function):
        before = set(browser.window_handles)
        a_function()
        after = set(browser.window_handles)
        new_windows = after - before
        assert 1 == len(new_windows), 'multiple windows opened by function'
        return new_windows.pop()
    
    # multiple windows
    
    second_window_handle = window_handle_opened_by(lambda: browser.execute_script('window.open()'))
    with window(browser, second_window_handle):
        browser.get(flask_uri)
        set_value(by_label("input_label"), 'second window')
        assert browser.find_element(*by_label('input_label')).get_attribute('value') == 'second window'
    
    assert browser.find_element(*by_label('input_label')).get_attribute('value') == 'first window'

def is_modal_present(browser):
    return EC.alert_is_present()(browser)

def test_basic_auth(browser, flask_uri):
    """
    - Selenium doesn't support basic auth dialogs natively
    - but user:pass@uri does work well enough
    """
    # Strangely capybara is missing support to access auth dialogs
    # However, the api for alerts, prompts and cofirms can at least be used to get rid of the dialog
    browser.get(flask_uri + '/basic_auth')
    
    # easy to dismiss auth alert
    browser.switch_to.alert.dismiss()
    text = browser.find_element(By.XPATH, '//body').text
    assert text == 'You need to authenticate'
    
    assert not is_modal_present(browser)
    
    # In the past it was possible to authenticate like this
    # browser.get(flask_uri + '/basic_auth')
    # browser.switch_to.alert.send_keys('user\tpass\n')
    # but with marionette / w3c driver, that doesn't work anymore, because of 
    # https://github.com/w3c/webdriver/issues/385
    
    # Selenium does not support auth prompts, so the password has to be submitted in the URL
    # Requires preference: network.http.phishy-userpass-length
    browser.get(add_auth_to_uri(flask_uri, 'admin', 'password') + '/basic_auth')
    
    text = browser.find_element(By.XPATH, '//body').text
    assert text == 'Authenticated'