# https://github.com/Microsoft/playwright-python
# Does not use selenium. Does not seem to use Webdriver, uses special Browser-Builds instead.
# Does have access to almost all browser behaviour, even stuff that is hard to do with selenium
# - like downloads, file choosers
# - Can record video of test run
# - can control ajax requests


from playwright.sync_api import PdfMargins, sync_playwright

import pytest

from conftest import assert_is_png, assert_is_file, assert_no_slower_than

HEADLESS = True
HEADLESS = False

@pytest.fixture
def page():
    with sync_playwright() as playwright:
        browser = playwright.firefox.launch(headless=HEADLESS)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(5000)
        yield page
        browser.close()

def test_google(page):
    """
    - Quite low level
    - Explicit waiting. Ugh
    - Self-Downloads browsers, nicely self contained
    - Not based on Selenium / Webdriver
    """
    
    page.goto('https://google.com/')
    page.click('text=Ich stimme zu')
    page.fill('css=[title=Suche]', 'Playwright')  # does not give focus!
    page.click('css=[value="Google Suche"]:visible')  # Not automatically choosing visible elment
    page.wait_for_load_state("networkidle")  # wtf is this neccessary?
    assert len(page.query_selector_all('.g')) >= 9
    content = page.text_content('css=.g:first-child')
    assert 'Playwright enables reliable end-to-end testing for modern web apps' in content

def test_nested_select_with_retry(page, flask_uri):
    """
    - complex assertionss are possible, but quite cumbersome through complex css or xpath
    """
    page.goto(flask_uri + '/dynamic_disclose')
    page.click('text=Trigger')
    inner = page.wait_for_selector('css=#outer >> css=#inner:has-text("fnord")')
    assert 'fnord' in inner.text_content()

def test_fill_form(page, flask_uri):
    """
    - placeholder not supported for text selector - why?
    - input_value behaves differently with text= selector engine
    """
    page.goto(flask_uri + '/form')
    page.fill('text=First name', 'Martin')
    page.fill('text=Last name', 'Häcker')
    page.fill('[placeholder="your@email"]', 'foo@bar.org')
    
    # text=First name doesn't work as it selects the label instead
    assert 'Martin' == page.input_value('#first_name')
    assert 'Häcker' == page.input_value('#last_name')
    assert 'foo@bar.org' == page.input_value('#email')

def test_fallback_to_selenium_and_js(page, flask_uri):
    """
    - What does escaping even mean here? Is there a lower level?
    """
    
    page.goto(flask_uri + '/form')
    element = page.query_selector('text=First name')
    
    assert element.evaluate('1+1') == 2
    
    # hard to get the current tag name
    assert element.evaluate('e => e.tagName') == 'LABEL'
    assert element.get_property('tagName').json_value() == 'LABEL'
    
    # js element selection is possible, but complicated
    assert element.evaluate_handle('e => e.parentElement').get_property('tagName').json_value() == 'FORM'

def test_select_by_different_criteria(page, flask_uri, xpath):
    """
    - `page.query_selector()` does _not_ autowait, `page.wait_for_selector()` does that instead
    - The different methods accept a common set of arguments to query for stuff, but can interpret it quite 
      different (e.g. text=label finds the input in `page.fill()`, but the label in `page.query_selector()`)
    - wrong usage / argument erors can lead to js exceptions which are hard to read
    - Much more low level, cannot specify freely what I'm searching, everything has to be very explicit _all_ the time
    - xpath selector library integration works ok
    """
    page.goto(flask_uri + '/selector_playground')
    
    # Can't locate input this way, even though it works for page.fill()
    assert page.query_selector('text=input_label').get_attribute('id') == 'label'
    
    def assert_field(*args, **kwargs):
        assert page.query_selector(*args, **kwargs).get_attribute('id') == 'input_id'
    
    # simple criterias
    # explicit attributes via css selectors work of course, but shorthands do not
    assert_field('[name=input_name]')
    assert_field('[title=input_title]')
    assert_field('[placeholder=input_placeholder]')
    assert_field('[value=input_value]')
    
    # selection by regex works, but not as part of a css selector
    assert page.query_selector('text=/input_.abel/').get_attribute('id') == 'label'
    
    # css/xpath
    assert_field('#input_id')
    # xpat is picky, can't leave out the object to select (e.g. '*' here)
    assert_field('xpath=//*[@class="input_class"]')
    
    # Aria, only by explicit access
    assert_field('[aria-label=input_aria_label]')
    
    # Complex criteria - can combine different criteria, but the different selectors,
    # i.e. 'text=' and 'css='
    assert_field('#input_id[aria-label=input_aria_label][placeholder=input_placeholder]')
    
    # xpath library integration works
    assert_field('xpath=' + xpath.field('input_label'))

def test_debugging_support(page, flask_uri, tmp_path):
    """
    - getting the html of a selection is not intuitive
    - screenshots, even of parts of page!
    - video of the test. Very nice!
    - har file of the test execution. Very nice!
    - tracing API that contains screenshots of every step of the test execution, 
      a har file and a full playwright trace. And it can be opened in a playwright viewer! Oh my.
    """
    page.goto(flask_uri + '/selector_playground')
    field = page.query_selector('input')
    
    # get html of page
    assert '<label for' in page.content()
    # get html of a selection
    assert field.get_property('outerHTML').json_value().startswith('<input id=')
    
    # get screenshot of page
    path = tmp_path / 'full_screenshot.png'
    page.screenshot(path=path)
    assert_is_png(path)
    # get screenshot of part of page
    path = tmp_path / 'partial_screenshot.png'
    field.screenshot(path=path)
    assert_is_png(path)
    
    # get video, har and trace of test
    browser = page.context.browser
    video_dir = tmp_path / 'videos'
    har_path = tmp_path / 'recorded.har'
    trace_path = tmp_path / 'trace.zip'
    context = browser.new_context(record_video_dir=video_dir, record_har_path=har_path)
    context.tracing.start(screenshots=True, snapshots=True)
    page = context.new_page()
    page.goto(flask_uri + '/selector_playground')
    page.fill('text=input_label', 'fnord')
    context.tracing.stop(path=trace_path)
    context.close() # save video and har files
    
    # video plays
    video_paths = list(video_dir.iterdir())
    assert len(video_paths) == 1
    video_path = video_paths[0]
    assert_is_file(video_path, '.webm', b'.webm: WebM')
    
    # har
    assert_is_file(har_path, '.har', b'/recorded.har: JSON data')
    
    # trace
    assert_is_file(trace_path, '.zip', b'/trace.zip: Zip archive data')
    # Trace contains har file, screenshots of every step 
    # and a full trace of playwright commands sent to the browser.
    # Wooot!

def test_isolation(page, flask_uri, ask_to_leave_script):
    """
    - test isolation is achieved at the context level
    - each test is supposed to get a new context, but share the browser (so that's what I'm emulating here)
        https://playwright.dev/python/docs/browser-contexts
    """
    page.goto(flask_uri)
    
    # set cookie
    # Capybara has no api to deal with cookies -> fallback to selenium
    page.context.add_cookies([dict(
        name='test_cookie', value='test_value', url=flask_uri,
    )])
    
    cookies = page.context.cookies()
    assert len(cookies) == 1
    assert cookies[0]['name'] == 'test_cookie'

    # write local storage
    page.evaluate("window.localStorage.setItem('test_key', 'test_value_localstorage')")
    assert page.evaluate("window.localStorage.getItem('test_key')") == 'test_value_localstorage'
    
    # write session storage
    page.evaluate("window.sessionStorage.setItem('test_key', 'test_value')")
    assert page.evaluate("window.sessionStorage.getItem('test_key')") == 'test_value'
    
    # open tab / window
    context = page.context
    assert len(context.pages) == 1
    new_page = context.new_page()  # actually opens a new tab
    assert len(context.pages) == 2
    assert page != new_page
    
    # open alert
    new_page.goto(flask_uri)
    # playwright actually doesn't like oepn alerts and auto closes them automatically
    # if that is not wanted, a handler has to be added with page.on('dialog')
    # This way it does stay open
    new_page.evaluate("setTimeout(\"alert('alert_message')\", 0)")
    
    # delay unload
    third_page = context.new_page()
    third_page.goto(flask_uri)
    third_page.evaluate(ask_to_leave_script)
    
    # beforeunload handlers need to be explicitly triggered
    # but I can't get them to run. :-(
    def handle_dialog(dialog):
        assert dialog.type == 'beforeunload'
        dialog.dismiss()

    third_page.on('dialog', handle_dialog)
    third_page.close(run_before_unload=True)
    
    # This is the big reset
    # quite fast!
    with assert_no_slower_than(1):
        browser = page.context.browser
        context.close()
        context = browser.new_context()
        page = context.new_page()
    
    # windows gone - no delay!
    assert len(context.pages) == 1
    assert page.url == 'about:blank'
    
    page.goto(flask_uri)
    
    # cookies gone
    assert len(context.cookies()) == 0
    
    # local storage gone
    assert page.evaluate("window.localStorage.length") == 0
    assert page.evaluate("window.sessionStorage.length") == 0
