# https://github.com/elliterate/capybara.py
# https://elliterate.github.io/capybara.py/

import re

import capybara
from capybara.dsl import page
from capybara.selenium.driver import Driver
from selenium import webdriver
from selenium.common.exceptions import ElementClickInterceptedException, ElementNotInteractableException

from conftest import assert_is_png, assert_no_slower_than, find_application, add_auth_to_uri
import pytest

HEADLESS = True
HEADLESS = False

@capybara.register_driver("selenium-firefox")
def init_firefox(app):
    options = webdriver.FirefoxOptions()
    options.binary_location = find_application('Firefox')
    options.headless = HEADLESS
    # otherwise marionette automatically disables beforeunload event handling
    # still requires interaction to trigger
    options.set_preference("dom.disable_beforeunload", False)
    
    return Driver(app, browser="firefox", options=options,
        # cannot set these after the fact, so we set them here
        clear_local_storage=True,
        clear_session_storage=True,
    )

@capybara.register_driver("selenium-chrome")
def init_chrome(app):
    """
    - Mostly behaves very similar to firefox
    - a bit less well supported (alerts in background, access to basic auth dialogs)
    - noticable faster
    """
    options = webdriver.ChromeOptions()
    options.binary_location = find_application('Google Chrome')
    options.headless = HEADLESS
    
    return Driver(app, browser="chrome", options=options,
        # cannot set these after the fact, so we set them here
        clear_local_storage=True,
        clear_session_storage=True,
    )

@capybara.register_driver('selenium-safari')
def init_safari(app):
    """
    - very much more limited than either firefox or chrome
    - does not (easily?) support creating a custom testing profile, 
      so normal plugins, bookmarks, cookies, saved passwords etc. can interfere
    - not possible to switch to Safari Technology Preview
    """
    
    return Driver(app, browser='safari',
        # executable_path is actually the path to the safaridriver, not to a custom safari version
        # executable_path=find_application('Safari Technology Preview', executable_name='safaridriver'),
        # cannot set these after the fact, so we set them here
        clear_local_storage=True,
        clear_session_storage=True
    )

capybara.default_driver = "selenium-firefox"
capybara.default_max_wait_time = 5

@pytest.fixture(scope='function', autouse=True)
def configure_driver(browser_vendor):
    with capybara.using_driver(f"selenium-{browser_vendor}"):
        yield

@pytest.fixture(scope='session', autouse=True)
def configure_base_url(flask_uri):
    capybara.app_host = flask_uri

@pytest.mark.xfail_safari(reason='session not clear, google consent cookie already present')
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

def test_nested_select_with_retry():
    """
    - nested searching just works. Ah the joy.
    - expressive find() is a joy to use
    """
    page.visit('/dynamic_disclose')
    page.click_on('Trigger')  # Don't care wether it's a link or button
    inner = page.find('#outer').find('#inner', text='fnord')
    assert 'fnord' in inner.text

@pytest.mark.xfail_safari(reason="fill_in doesn't work")
def test_fill_form():
    """
    - as does searching by label or placeholder
    """
    page.visit('/form')
    page.fill_in('First name', value='Martin')
    page.fill_in('Last name', value='Häcker')
    page.fill_in('your@email', value='foo@bar.org')
    
    assert 'Martin' == page.find_field('First name').value
    assert 'Häcker' == page.find_field('Last name').value
    assert 'foo@bar.org' == page.find_field('your@email').value

def test_fallback_to_selenium_and_js():
    """
    - simple escaping to selenium
    - simple access to the selected dom node from js
    - wraps returned dom nodes into the native element
    """
    page.visit('/form')
    
    browser = page.driver.browser
    from selenium import webdriver
    assert isinstance(browser, webdriver.Remote)
    
    element = page.find_field('First name')
    
    from selenium.webdriver.remote.webelement import WebElement
    assert isinstance(element.native, WebElement)
    
    element.native.send_keys('fnord')
    assert element.value == 'fnord'
    
    # Can even return the correct wrapper element for dom references!
    # Safari returns tag names uppercase
    assert element.evaluate_script('this.parentElement').tag_name.lower() == 'form'

def test_select_by_different_criteria():
    """
    - Just a joy to select stuff - every imaginable way just works
    """
    page.visit('/selector_playground')
    
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

def test_debugging_support(tmp_path):
    """
    - not very much special debugging support
    - getting at the html for a selection is not intuitive
    - capybara doesn't seem to expose a way to differentiate between html attributes and js properties
    """
    page.visit('/selector_playground')
    field = page.find_field('input_name')
    
    # get html of page
    assert '<label for' in page.html
    # get html of a selection
    assert field['outerHTML'].startswith('<input id=')
    
    # get screenshot of page
    path = tmp_path / 'full_screenshot.png'
    page.save_screenshot(path)
    assert_is_png(path)

def test_isolation(ask_to_leave_script):
    """
    - easy fast reset between tests, that resets pretty much everything that normal web applications use
    - cookies, localStorage, sessionStorage (though *Storage only if configured)
    - can deal with unload events that display a dialog (even though Firefox webdriver doesn't show them)
    - open alerts in background windows are _not_ consistently closed on reset(). (FF works, Chrome doesn't)
    """
    page.visit('/')
    
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
    # here the capybara api reads a bit strange. It talks about windows, but actually means tabs,
    # and there seems to be no way to actually open a new window
    original_window = page.current_window
    assert len(page.windows) == 1
    new_window = page.open_new_window()  # actually opens a new tab
    assert len(page.windows) == 2
    assert original_window != new_window
    
    ## alerts in background windows are _not_ consistently closed when the browser is reset
    ## Works in Firefox, but not in Chrome
    # with page.window(new_window):
    #     page.evaluate_script("alert('alert_message')")
    
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
    #     page.visit('/')
    #     page.execute_script(ask_to_leave_script)
    #     # page interaction, so onbeforeunload is actually triggered
    #     page.fill_in('input_label', value='fnord')
    
    # Google Chrome doesn't close dialog in background window. Bug in chromedriver?
    
    # reset() is where the magic happens
    # only reset local- and sessionStorage if configured in Driver()
    with assert_no_slower_than(1):
        page.reset()
    
    assert len(page.windows) == 1
    assert page.current_url == 'about:blank'
    
    page.visit('/')
    
    # cookies gone
    assert len(page.driver.browser.get_cookies()) == 0
    
    # local storage gone
    assert page.evaluate_script("window.localStorage.length") == 0
    assert page.evaluate_script("window.sessionStorage.length") == 0

@pytest.mark.xfail_safari(reason="Safari doesn't support beforeunload")
def test_dialogs(ask_to_leave_script):
    """
    - Surprisingly there is no way to check wether any js alert is visible
    - Selenium is not nice, but at least it provides a fallback
    """
    page.visit('/')
    # accepting or dismissing an anticipated alert ist simple
    with page.accept_alert():
        # does not block on evaluating `alert()`!
        page.evaluate_script('alert("fnord")')
    
    # detect that an alert is currently being shown
    page.evaluate_script('alert("fnord")')
    # no official api?
    # There is private API, that can be used to detect a modal is present, but fails if it is not
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

@pytest.mark.xfail_safari(reason="fill_in doesn't work")
def test_working_with_multiple_window():
    """
    - Surprisingly the capybara API doesn't have a window object that also inherits the capybara dsl.
      Thus it doesn't seem possible to talk to a specific window directly
    - Other than that, working with multiple windows is a breeze
    """
    page.visit('/')   
    page.fill_in('input_label', value='first window')
    # multiple windows
    with page.window(page.open_new_window()):
        page.visit('/')
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
        page.visit('/')
        page.fill_in('input_label', value='third window')
    
    assert page.find_field('input_label').value == 'first window'
    # or explicitly
    page.switch_to_window(window)
    # now the API interacts with that window
    assert page.find_field('input_label').value == 'third window'

@pytest.mark.xfail_safari(reason='cannot open multiple concurrent browsers')
def test_work_with_multiple_browsers():
    """
    - simple and consistent.
    - can be used via conext manager or via explicit session objects (though slightly more complicated)
    """
    page.visit('/')
    page.fill_in('input_label', value='first browser')
    
    with capybara.using_session('second browser'):
        page.visit('/')
        page.fill_in('input_label', value='second browser')

    assert page.find_field('input_label').value == 'first browser'
    
    with capybara.using_session('second browser'):
        assert page.find_field('input_label').value == 'second browser'

def is_modal_present():
    # The only way capybara allows to check for an alert is to use the private API _find_modal() 
    # which raises if no dialog is present
    try:
        with capybara.using_wait_time(0):
            # _find_modal(wait=0) waits way longer than using_wait_time()
            page.driver._find_modal(wait=0)
        return True
    except capybara.exceptions.ModalNotFound as ignored:
        return False
    
    # Falling back to selenium would actually be simpler and cleaner
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    return EC.alert_is_present()(page.driver.browser)

@pytest.mark.skipif_safari(reason="basic auth not supported at all on safari")
def test_basic_auth(flask_uri):
    """
    - capybara does not natively support a way to check wether a modal dialog is present
    - python does not make it easy to add a username:password@url to a url. Why?
    - surprisingly Firefox does not complain about username:password@url urls and just accepts it.
    """
    ## Strangely selenium (and thus capybara) is missing support to access auth dialogs
    ## On some browsers (Firefox) the alert api allows some interaction with auth dialogs.
    ## But that is really too brittle to be used in production.
    # with page.dismiss_prompt():
    #     page.visit('/basic_auth')
    # assert page.text == 'You need to authenticate'
    # assert not is_modal_present()
    
    # Selenium does not support auth prompts, so the password has to be submitted in the URL
    # alternative is to add username:password@ befor the host in the url, but most browsers  
    # requires a custom setting to re-enable this feature.
    # Firefox: network.http.phishy-userpass-length 255 (currently enabled automatically)
    page.visit(add_auth_to_uri(flask_uri, 'admin', 'password') + '/basic_auth')
    assert not is_modal_present()
    assert page.text == 'Authenticated'

def is_in_viewport(element):
    viewport_height = page.evaluate_script('window.innerHeight')
    viewport_width = page.evaluate_script('window.innerWidth')
    scroll_from_top = page.evaluate_script('window.scrollY')
    scroll_from_left = page.evaluate_script('window.scrollY')
    
    client_rect = element.evaluate_script('this.getBoundingClientRect()')
    
    return not (
        client_rect['top'] > viewport_height + scroll_from_top
        or client_rect['left'] > viewport_width + scroll_from_left
        or  client_rect['bottom'] < scroll_from_top
        or client_rect['right'] < scroll_from_left
    )

@pytest.mark.xfail_safari(reason="""Deems text of invisible elements visible,
and raises different exceptions than ElementClickInterceptedException""")
def test_invisible_and_hidden_elements():
    """
    - capybara by default doesn't find elements that are hidden in any way
    - capybara has three attributes to get at the text of elements 
        - all_text (js text_content)
        - visible_text (basically native.text)
        - text (either all_text or visible_text depending on capybara.ignore_hidden_elements or capybara.visible_text_only)
    - Surprisingly capybara doesn't provide a utility to check whether an element is outside the viewport. js to the rescue
    """
    page.visit('/hidden')
    # Ensure the page is rendered
    assert page.find('.visible').text == 'Visible because just normal content in the body'
    
    def assert_visibility(
        selector, *, is_visible, text,
        interaction_exception=ElementNotInteractableException
    ):
        assert page.find(selector, visible=False).all_text.startswith('Hidden because')
        # assert page.find(selector, visible=False).text == text
        # assert page.find(selector, visible=False).visible_text == text
        
        if not is_visible:
            # raises if element is invisible, cannot accentally ignore
            with pytest.raises(capybara.exceptions.ElementNotFound):
                page.find(selector)
        
        # raises if element is invisible, cannot accidentally interact with hidden element
        with pytest.raises(interaction_exception):
            page.find(selector, visible=False).click()

    # So convenient that this can be set using a context manager.
    # For a test, an API that would hook into a teardown API could be nicer, as it doesn't indent the code
    # But that requires integration from the API to (all) the test frameworks. So...
    with capybara.using_wait_time(0):
        assert_visibility('.invisible', is_visible=False, text='')
        assert_visibility('.removed', is_visible=False, text='')
        assert_visibility('.out_of_frame', is_visible=False, text='')
        assert_visibility('.behind', is_visible=True, text='Hidden because behind another div',
            interaction_exception=ElementClickInterceptedException
        )
        
        # Content scrolled out of view
        # capybara is missing support to check wether an element is scrolled into view
        assert not is_in_viewport(page.find('.below_scroll'))
        assert page.find('.below_scroll').text == 'Visible but scrolled out ouf view'
        # will auto scroll into view
        page.find('.below_scroll').click()
        assert is_in_viewport(page.find('.below_scroll'))
