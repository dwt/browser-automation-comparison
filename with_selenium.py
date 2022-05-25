# https://www.selenium.dev/selenium/docs/api/py/

from contextlib import contextmanager

import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    ElementClickInterceptedException, ElementNotInteractableException, NoSuchElementException,
    NoSuchShadowRootException
)
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

from conftest import find_application, assert_is_png, add_auth_to_uri

import pytest

from objexplore import explore as e
from rich import inspect as i

WAIT = 2

def firefox(is_headless):
    options = webdriver.FirefoxOptions()
    options.headless = is_headless
    # required or marionette will not allow beforeunload dialogs
    options.set_preference("dom.disable_beforeunload", False)
    # required to allow username and password in url for basic auth
    # http://kb.mozillazine.org/Network.http.phishy-userpass-length
    # currently set automatically
    # options.set_preference('network.http.phishy-userpass-length', 255)
    options.binary_location = find_application('Firefox')
    
    service = FirefoxService(GeckoDriverManager().install())
    
    return webdriver.Firefox(options=options, service=service)

def chrome(is_headless):
    options = webdriver.ChromeOptions()
    options.binary_location = find_application('Google Chrome')
    options.headless = is_headless
    
    service = ChromeService(ChromeDriverManager().install())
    
    return webdriver.Chrome(options=options, service=service)
    
def safari(is_headless):
    """
    - no headless support
    - strange differences
        - returns uppercase tag names
    - can be really slow to start
    - no isolated profile, really annoying
    """
    return webdriver.Safari()

def remote(is_headless):
    """
    - Run tests in ff,chrome,edge in docker
    - observe with vnc or browser based vnc
    - vnc built into selenium grid sucks, because it requires a reconnect for each session, i.e. for each test run
    - possible to record videos from vnc (sidecar docker container for this is available)
    - FF and Chrome work well
    - Surprisingly fast browser restarts
    """
    
    # see the autouse fixuture `run_firefox_in_docker_if_using_remote()` which starts docker in the background
    options = webdriver.FirefoxOptions()
    # required or marionette will not allow beforeunload dialogs
    options.set_preference("dom.disable_beforeunload", False)
    # options = webdriver.ChromeOptions()
    return webdriver.Remote(command_executor='http://localhost:4444', options=options)

@pytest.fixture
def browser(browser_vendor, run_selenium_firefox_in_docker_if_neccessary, is_headless):
    browsers = {
        'firefox': firefox,
        'chrome': chrome,
        'safari': safari,
        'remote-selenium': remote,
    }
    browser = browsers[browser_vendor](is_headless)
    browser.implicitly_wait(WAIT)
    try:
        yield browser
    finally:
        browser.quit()

browser2 = browser

def until(driver, condition, wait=WAIT):
    driver.implicitly_wait(0)
    try:
        return WebDriverWait(driver, wait).until(condition)
    finally:
        driver.implicitly_wait(WAIT)

@pytest.mark.xfail_safari(reason="Safari doesn't isolate the test session with it's own profile, thus the google cookie interferes")
def test_google(browser):
    """
    - can auto wait
    - increadibly basic selector support, no support for compound stuff (class + text) out of the box
    - quite verbose…
    - need an explicit wait or test heisenbugs if google is slow
    """
    
    browser.get('http://google.com/')
    assert 'Google' in browser.title
    
    browser.find_element(By.XPATH, '//button[normalize-space()="Ich stimme zu"]').click()
    search_field = browser.find_element(By.CSS_SELECTOR, '[title="Suche"]')
    search_field.send_keys('Selenium' + Keys.RETURN)
    
    # Need explicit wait, or the next assertion fires before the page has finished loading
    until(browser, EC.presence_of_element_located((By.CLASS_NAME, 'g')))
    
    assert len(browser.find_elements(By.CSS_SELECTOR, '.g')) >= 9
    
    elements = browser.find_elements(By.CSS_SELECTOR, '.g')
    assert any(map(lambda each: 'Selenium automates browsers' in each.text, elements))

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
    
    assert 'Martin' == browser.find_element(By.ID, 'first_name').get_attribute('value')
    assert 'Häcker' == browser.find_element(By.ID, 'last_name').get_attribute('value')
    assert 'foo@bar.org' == browser.find_element(By.ID, 'email').get_attribute('value')

def test_fallback_to_selenium_and_js(browser, flask_uri):
    """
    - selection by js is possible but cumbersome
    """
    browser.get(flask_uri + '/form')
    element = browser.find_element(*by_label("First name"))
    parent_element = browser.execute_script('return arguments[0].parentElement', element)
    # safari returns uppercase tag names
    assert parent_element.tag_name.lower() == 'form'

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

@pytest.mark.xfail_safari(reason='beforeunload not supported')
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

@pytest.mark.skipif_safari(reason='does not support multiple open browsers')
def test_work_with_multiple_browsers(browser, browser2, flask_uri):
    """
    - fairly straight forward, just create a second browser and go
    - pytest fixture gives fairly nice lifecycle management
    """
    def fill_in(browser, label, value):
        element = browser.find_element(*by_label(label))
        element.clear()
        element.send_keys(value)
    
    browser.get(flask_uri)
    fill_in(browser, 'input_label', 'first browser')
    
    browser2.get(flask_uri)
    fill_in(browser2, 'input_label', 'second browser')
    
    assert browser.find_element(*by_label('input_label')).get_attribute('value') == 'first browser'
    assert browser2.find_element(*by_label('input_label')).get_attribute('value') == 'second browser'

def is_modal_present(browser):
    return EC.alert_is_present()(browser)

@pytest.mark.skipif_safari(reason="does not support basic auth at all")
def test_basic_auth(browser, flask_uri):
    """
    - Selenium doesn't support basic auth dialogs natively
    - but user:pass@uri does work well enough
    """
    ## Strangely selenium is missing support to access auth dialogs
    ## However, the api for alerts, prompts and cofirms can at least be used to get rid of the dialog
    ## Firefox can at least close the dialog, but chrome and webkit are helpless
    ## That means it is not possible to test what happens if basic auth fails
    ## which is usually not a problem.
    # browser.get(flask_uri + '/basic_auth')
    # # easy to dismiss auth alert
    # browser.switch_to.alert.dismiss()
    # text = browser.find_element(By.XPATH, '//body').text
    # assert text == 'You need to authenticate'
    # assert not is_modal_present(browser)
    
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

def is_in_viewport(browser, element):
    viewport_height = browser.execute_script('return window.innerHeight')
    viewport_width = browser.execute_script('return window.innerWidth')
    scroll_from_top = browser.execute_script('return window.scrollY')
    scroll_from_left = browser.execute_script('return window.scrollY')
    
    client_rect = browser.execute_script('return arguments[0].getBoundingClientRect()', element)
    
    return not (
        client_rect['top'] > viewport_height + scroll_from_top
        or client_rect['left'] > viewport_width + scroll_from_left
        or  client_rect['bottom'] < scroll_from_top
        or client_rect['right'] < scroll_from_left
    )

@contextmanager
def using_wait_time(browser, wait_time):
    browser.implicitly_wait(wait_time)
    try:
        yield
    finally:
        browser.implicitly_wait(WAIT)

@pytest.mark.xfail_safari(reason='invisible content is deemed visible')
def test_invisible_and_hidden_elements(flask_uri, browser):
    """
    - cannot set / reduce implicit wait time via context manager
    - cannot get current implicit wait time
    - treats content hidden behind other elements as visible
        - but at least raises when trying to interact with it
    - Surprisingly capybara doesn't provide a utility to check whether an element is outside the viewport. js to the rescue
    """
    browser.get(flask_uri + '/hidden')
    
    def find(css_selector):
        "way to long to type out every time"
        return browser.find_element(By.CSS_SELECTOR, css_selector)
    
    # Ensure the page is rendered
    assert find('.visible').text == 'Visible because just normal content in the body'
    
    def assert_visibility(
        selector, *, is_visible, text,
        interaction_exception=ElementNotInteractableException
    ):
        # invisible elements are returned jus as well
        assert find(selector) is not None
        # but at least they know wether they are visible
        assert find(selector).is_displayed() is is_visible
        
        # no API to get the text wether it is visible or not, can just get the visible text
        assert find(selector).text == text
        # js can get all the text if needed
        assert find(selector).get_attribute('textContent').startswith('Hidden because')
        
        with pytest.raises(interaction_exception):
            find(selector).click()
    
    # no support to get the wait time or set / reduce it via context magager.
    # Also hard to build yourself, because there is no getter for the current wait time
    with using_wait_time(browser, 0):
        # All of this makes sense
        assert_visibility('.invisible', is_visible=False, text='')
        assert_visibility('.removed', is_visible=False, text='')
        assert_visibility('.out_of_frame', is_visible=False, text='')
        # Strange that the browser doesn't understand that this element is invisible
        # at least it understands that it cannot be clicked
        assert_visibility(
            '.behind', is_visible=True, text='Hidden because behind another div',
            interaction_exception=ElementClickInterceptedException
        )
        
        # Content scrolled out of view
        # capybara is missing support to check wether an element is scrolled into view
        assert not is_in_viewport(browser, find('.below_scroll'))
        assert find('.below_scroll').text == 'Visible but scrolled out ouf view'
        # will auto scroll into view
        find('.below_scroll').click()
        assert is_in_viewport(browser, find('.below_scroll'))