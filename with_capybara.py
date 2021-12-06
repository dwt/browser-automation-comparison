# https://github.com/elliterate/capybara.py

import re

import capybara
from capybara.dsl import page
from selenium.webdriver.common.keys import Keys

import pytest
from conftest import assert_is_png, assert_no_slower_than, find_firefox

HEADLESS = True
# HEADLESS = False

@capybara.register_driver("selenium")
def init_selenium_driver(app):
    
    from selenium.webdriver.firefox.options import Options
    options = Options()
    options.binary_location = find_firefox()
    options.headless = HEADLESS
    # otherwise marionette automatically disables beforeunload event handling
    # still requires interaction to trigger
    options.set_preference("dom.disable_beforeunload", False)
    
    from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
    
    capabilities = DesiredCapabilities.FIREFOX.copy()
    capabilities["marionette"] = True
    
    from capybara.selenium.driver import Driver
    
    return Driver(app, browser="firefox", options=options, desired_capabilities=capabilities,
        # cannot set these after the fact, so we set them here
        clear_local_storage=True,
        clear_session_storage=True,
    )


capybara.default_driver = "selenium"
capybara.default_max_wait_time = 5

def test_google():
    """
    - Complicated setup to set custom firefox path
    - pretty much the original capybara api. Nice!
    - just running generates warnings :-(
    """
    
    page.visit("https://google.com")
    page.click_button('Ich stimme zu')
    page.fill_in(title='Suche', value='Selenium')
    # sadly doesn't return the found object, so no chaining
    # .send_keys(Keys.RETURN)
    # looks more like a bug than intention
    
    # There are two buttons, though technically only one of them should be visible
    page.click_button('Google Suche', match='first')
    
    assert len(page.find_all('.g')) >= 10
    assert page.has_selector('.g', text='Selenium automates browsers')
    
    capybara.reset_sessions()

def test_nested_select_with_retry(flask_uri):
    """
    - nested searching just works. Ah the joy.
    - expressive find() is a joy to use
    """
    page.visit(flask_uri + '/dynamic_disclose')
    page.click_on('Trigger')  # Don't care wether it's a link or button
    inner = page.find('#outer').find('#inner', text='fnord')
    assert 'fnord' in inner.text

def test_fill_form(flask_uri):
    """
    - as does searching by label or placeholder
    """
    page.visit(flask_uri + '/form')
    page.fill_in('First name', value='Martin')
    page.fill_in('Last name', value='Häcker')
    page.fill_in('your@email', value='foo@bar.org')
    
    assert 'Martin' == page.find_field('First name').value
    assert 'Häcker' == page.find_field('Last name').value
    assert 'foo@bar.org' == page.find_field('your@email').value

def test_fallback_to_selenium_and_js(flask_uri):
    """
    - simple escaping to selenium
    - simple access to the selected dom node from js
    - wraps returned dom nodes into the native element
    """
    page.visit(flask_uri + '/form')
    
    browser = page.driver.browser
    from selenium import webdriver
    assert isinstance(browser, webdriver.Firefox)
    
    element = page.find_field('First name')
    
    from selenium.webdriver.remote.webelement import WebElement
    assert isinstance(element.native, WebElement)
    
    element.native.send_keys('fnord')
    assert element.value == 'fnord'
    
    # Can even return the correct wrapper element for dom references!
    assert element.evaluate_script('this.parentElement').tag_name == 'form'

def test_select_by_different_criteria(flask_uri):
    """
    - Just a joy to select stuff - every imaginable way just works
    """
    page.visit(flask_uri + '/selector_playground')
    
    def assert_field(*args, **kwargs):
        assert page.find_field(*args, **kwargs).value == 'input_value'
    
    # simple criterias
    assert_field('input_name')
    assert_field(name='input_name')
    assert_field(title='input_title')
    assert_field('input_placeholder')
    assert_field(placeholder='input_placeholder')
    assert_field('input_label')
    assert_field(label='input_label')
    assert_field(label=re.compile('input_.abel')) # actually, regexes are supported on most (all?) kwargs
    assert_field(value='input_value')
    
    assert_field(id_='input_id')
    assert_field(class_='input_class')
    assert_field(css='#input_id')
    assert_field(xpath='//[@class=input_class]')
    
    # Aria
    capybara.enable_aria_label = True
    assert_field('input_aria_label')
    assert_field(aria_label='input_aria_label')
    
    # Complex criteria
    assert_field(id_='input_id', label='input_label', placeholder='input_placeholder')

def test_debugging_support(flask_uri, tmp_path):
    """
    - not very much special debugging support
    - getting at the html for a selection is not intuitive
    - capybara doesn't seem to expose a way to differentiate between html attributes and js properties
    """
    page.visit(flask_uri + '/selector_playground')
    field = page.find_field('input_name')
    
    # get html of page
    assert '<label for' in page.html
    # get html of a selection
    assert field['outerHTML'].startswith('<input id=')
    
    # get screenshot of page
    path = tmp_path / 'full_screenshot.png'
    page.save_screenshot(path)
    assert_is_png(path)


def test_isolation(flask_uri, ask_to_leave_script):
    """
    - easy fast reset between tests, that resets pretty much everything that normal web applications use
    - cookies, localStorage, sessionStorage (though *Storage only if configured)
    - can deal with unload events that display a dialog (even though Firefox webdriver doesn't show them)
    """
    page.visit(flask_uri)
    
    # set cookie
    # Capybara has no api to deal with cookies -> fallback to selenium
    page.driver.browser.add_cookie(dict(
        name='test_cookie', value='test_value'
    ))
    cookies = page.driver.browser.get_cookies()
    assert len(cookies) == 1
    assert cookies[0]['name'] == 'test_cookie'
    assert page.driver.browser.get_cookie('test_cookie')['value'] == 'test_value'

    # write local storage
    page.evaluate_script("window.localStorage.setItem('test_key', 'test_value_localstorage')")
    assert page.evaluate_script("window.localStorage.getItem('test_key')") == 'test_value_localstorage'
    
    # write session storage
    page.evaluate_script("window.sessionStorage.setItem('test_key', 'test_value')")
    assert page.evaluate_script("window.sessionStorage.getItem('test_key')") == 'test_value'
    
    # open tab / window
    # here the capybara api reads a bit strange. It talks about windows, but actually means tabs, and there seems to be no way to actually open a new window
    original_window = page.current_window
    assert len(page.windows) == 1
    new_window = page.open_new_window()  # actually opens a new tab
    assert len(page.windows) == 2
    assert original_window != new_window
    
    # open alert
    with page.window(new_window):
        page.evaluate_script("alert('alert_message')")
    
    # onbeforeunload dialogs
    # bug in capybara, ask to leave script is only handled in current window, other windows just get closed and then hang
    # see https://github.com/elliterate/capybara.py/issues/26
    # Even though it is handled in the code, that doesn't work for firefox. (?)
    # page.execute_script(ask_to_leave_script)
    # page interaction, so onbeforeunload is actually triggered
    # page.fill_in('input_label', value='fnord')
    
    # bug in capybara: background windows don't even have code to handle dialogs like onbeforeunload
    # see https://github.com/elliterate/capybara.py/issues/26
    # with page.window(page.open_new_window()):
    #     page.visit(flask_uri)
    #     page.execute_script(ask_to_leave_script)
    #     # page interaction, so onbeforeunload is actually triggered
    #     page.fill_in('input_label', value='fnord')


    
    # reset() is where the magic happens
    # only reset local- and sessionStorage if configured in Driver()
    with assert_no_slower_than(1):
        page.reset()
    
    # windows gone - no delay!
    assert len(page.windows) == 1
    assert page.current_url == 'about:blank'
    
    page.visit(flask_uri)
    
    # cookies gone
    assert len(page.driver.browser.get_cookies()) == 0
    
    # local storage gone
    assert page.evaluate_script("window.localStorage.length") == 0
    assert page.evaluate_script("window.sessionStorage.length") == 0

def test_dialogs(flask_uri):
    """
    - Surprisingly there is no way to check wether any js alert is visible
    - Selenium is not nice, but at least it provides a fallback
    """
    page.visit(flask_uri)
    # accepting or dismissing an anticipated alert ist simple
    with page.accept_alert():
        # does not block on evaluating `alert()`!
        page.evaluate_script('alert("fnord")')
    
    # detect that an alert is currently being shown
    page.evaluate_script('alert("fnord")')
    # no official api?
    # There is private API
    assert page.driver._find_modal() is not None
    # And there is the fallback to selenium
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    alert = WebDriverWait(page.driver.browser, 0).until(EC.alert_is_present())
    assert alert is not None
    alert.accept()
    # no good way to check that _no_ alert is present
    from selenium.common.exceptions import NoAlertPresentException
    with pytest.raises(NoAlertPresentException):
        page.driver.browser.switch_to.alert

def test_working_with_multiple_window(flask_uri):
    """
    - Surprisingly the capybara API doesn't have a window object that also inherits the capybara dsl.
      Thus it doesn't seem possible to talk to a specific window directly
    - Other than that, working with multiple windows is a breeze
    """
    page.visit(flask_uri)   
    page.fill_in('input_label', value='first window')
    # multiple windows
    with page.window(page.open_new_window()):
        page.visit(flask_uri)
        page.fill_in('input_label', value='second window')
        assert page.find_field('input_label').value == 'second window'
        # it's a bit strange that the page is a proxy to the /current page/ that is not explicit in the capybara api
    
    assert page.find_field('input_label').value == 'first window'
    
    # What is really simple though is getting a window reference to a window that is opened by the page (e.g. a click or js)
    window = page.window_opened_by(lambda: page.open_new_window())
    # that window is actually an object, but the capybara API seems not to be available on it.
    # instead one has to make it the 'current' window
    # Either via a context manager
    with page.window(window):
        page.visit(flask_uri)
        page.fill_in('input_label', value='third window')
    
    assert page.find_field('input_label').value == 'first window'
    # or explicitly
    page.switch_to_window(window)
    # now the API interacts with that window
    assert page.find_field('input_label').value == 'third window'
