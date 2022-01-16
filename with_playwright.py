# https://github.com/Microsoft/playwright-python
# Does not use selenium. Does not seem to use Webdriver, uses special Browser-Builds instead.
# Does have access to almost all browser behaviour, even stuff that is hard to do with selenium
# - like downloads, file choosers
# - Can record video of test run
# - can control ajax requests


from contextlib import contextmanager
from playwright.sync_api import PdfMargins, sync_playwright, TimeoutError

import pytest

from conftest import assert_is_png, assert_is_file, assert_no_slower_than, add_auth_to_uri

HEADLESS = True
HEADLESS = False

WAIT = 5000

@pytest.fixture(scope='session')
def browser():
    with sync_playwright() as playwright:
        # FIXME needs to launch firefox, chromium or webkit, 
        browser = playwright.firefox.launch(headless=HEADLESS)
        yield browser
        browser.close()

# contexts are what guarantees test isolation - every test gets a new one
@pytest.fixture
def context(browser):
    context = browser.new_context()
    yield context
    context.close()

# and can potentially open many pages, which are auto closed when the context is
@pytest.fixture
def page(context):
    page = context.new_page()
    page.set_default_timeout(WAIT)
    yield page

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
    assert len(page.query_selector_all('.g')) >= 8
    content = page.text_content('css=.g:first-child')
    assert 'Playwright: Fast and reliable end-to-end testing for modern' in content

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
    # page needs a change otherwise the onbeforeunload doesn't trigger
    third_page.fill('text=input_label', value='fnord')
    
    did_handle_beforeunload = False
    # beforeunload handlers need to be explicitly triggered
    # but I can't get them to run. :-(
    def handle_dialog(dialog):
        global did_handle_beforeunload
        did_handle_beforeunload = True
        assert dialog.type == 'beforeunload'
        dialog.dismiss()
    third_page.on('dialog', handle_dialog)
    third_page.close(run_before_unload=True)
    # Fails, not sure why that is, the dialog just doesn't show up
    # assert did_handle_beforeunload
    
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

def test_dialogs(page, flask_uri):
    """
    - No way to detect / get at an (already) open dialog
    - not possible to test page leave dialogs? Can't get them to show
    """
    # alerts
    page.goto(flask_uri)
    
    # accepting or dismissing an anticipated alert requires a handler
    def handle_dialog(dialog):
        assert dialog.type == 'alert'
        assert dialog.message == 'fnord'
        dialog.accept()
    
    page.on('dialog', handle_dialog)
    page.evaluate('alert("fnord")')
    # this closes all future dialogs
    page.evaluate('alert("fnord")')
    # but interestingly doesn't accept dialogs opened asynchronouslys
    page.evaluate('setTimeout(() => alert("fnord"), 0)')
    page.remove_listener('dialog', handle_dialog)
    # funny enough, triggering another alert dismisses both, 
    # it seems the standard listener (no listener) can clean up pretty well
    page.evaluate('alert("fnord")')
    
    # detect that an alert is currently being shown, i.e. how to deal with async code opening alerts?
    page.evaluate('setTimeout(() => alert("fnord"), 0)')
    # There seems to be no concept of either detecting them or dealing with them
    # Selenium at least has browser.switch_to.alert - but here, nothing?

def test_working_with_multiple_window(page, context, flask_uri):
    page.goto(flask_uri)
    page.fill('text=input_label', value='first window')
    
    # multiple windows
    with page.expect_popup() as popup:
        second_page = context.new_page()
        second_page.goto(flask_uri)
        second_page.fill_in('input_label', value='second window')
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

def test_work_with_multiple_browsers(page, browser, flask_uri):
    """
    - simple isolation with explicit objects representing the browsers
    - really likes to deadlock / hang with multiple browser on programming errors
    """
    page.goto(flask_uri)
    page.fill('text=input_label', value='first browser')
    
    # equivalent to second browser, as we get guaranteed isolation
    page2 = browser.new_context().new_page()
    page2.goto(flask_uri)
    page2.fill('text=input_label', value='second browser')
    
    assert page.input_value('#input_id') == 'first browser'
    assert page2.input_value('#input_id') == 'second browser'

def test_basic_auth(page, browser, flask_uri):
    """
    - basic auth in url works
    - basic auth in context works
    """
    # Strangely the authentication dialog is not shown at all
    page.goto(flask_uri + '/basic_auth')
    
    assert page.inner_text('body') == 'You need to authenticate'
    
    # Even though this is not documented, it works fine
    page.goto(add_auth_to_uri(flask_uri, 'admin', 'password') + '/basic_auth')
    # Thats because playwright auto enables the setting 
    # http://kb.mozillazine.org/Network.http.phishy-userpass-length
    # network.http.phishy-userpass-length 255

    assert page.inner_text('body') == 'Authenticated'
    
    # Accoring to the docs this is the recommended way to do basic authentication
    context = browser.new_context(
        http_credentials={"username": "admin", "password": "password"}
    )
    page = context.new_page()
    page.goto(flask_uri + '/basic_auth')
    assert page.inner_text('body') == 'Authenticated'

def is_in_viewport(page, element):
    viewport_height = page.evaluate('window.innerHeight')
    viewport_width = page.evaluate('window.innerWidth')
    scroll_from_top = page.evaluate('window.scrollY')
    scroll_from_left = page.evaluate('window.scrollY')
    
    rect = element.bounding_box()
    
    return not (
        rect['y'] > viewport_height + scroll_from_top
        or rect['x'] > viewport_width + scroll_from_left
        or rect['y'] + rect['height'] < scroll_from_top
        or rect['x'] + rect['width'] < scroll_from_left
    )

@contextmanager
def using_wait_time(page, wait_time):
    page.set_default_timeout(wait_time)
    try:
        yield
    finally:
        page.set_default_timeout(WAIT)

def test_invisible_and_hidden_elements(flask_uri, page):
    """
    - no utility to temporarily reduce the default timeout
    - timout of 0,1, <50 lead to various surprising errors, because internal checks of interactability cannot complete successfully.
        - bug or feature?
    - playwright has different and also strange ideas than selenium about what is considered visible
        - and what text is considered visible? (inner_text behaves strange)
    - very sensitive to short timeouts, because scrolling into view doesn't work anymore with very
      short timeouts, even if the element in question is already scrolled into view
    """
    page.goto(flask_uri + '/hidden')
    
    # Ensure the page is rendered
    assert page.query_selector('.visible').text_content() == 'Visible because just normal content in the body'
    
    def find(css_selector):
        "way to long to type out every time"
        return page.query_selector(css_selector)
    
    def assert_visibility(selector, *, is_visible, inner_text):
        assert find(selector) is not None
        # but at least they know wether they are visible
        assert find(selector).is_visible() is is_visible
        
        # inner == sometimes is the visible text, but not always
        assert find(selector).inner_text() == inner_text
        # js can get all the text if needed
        assert find(selector).text_content().startswith('Hidden because')
        
        # raises while trying to wait for elements to be visible, enabled and stable
        with pytest.raises(TimeoutError):
            find(selector).click()
    
    # no support to get the wait time or set / reduce it via context magager.
    # Also hard to build yourself, because there is no getter for the current wait time
    # wait times below 50 lead to errors, because playwright is not able to execute it's internal checks
    with using_wait_time(page, 100):
        assert_visibility('.invisible', is_visible=False, inner_text='')
        # interesting that inner text of these hidden elements is returned?
        assert_visibility('.removed', is_visible=False, inner_text='Hidden because display:none')
        # strange that the moved out of frame element is considered visible
        assert_visibility('.out_of_frame', is_visible=True, inner_text='Hidden because moved out of frame')
        
        assert_visibility('.behind', is_visible=True, inner_text='Hidden because behind another div')
        
        # Content scrolled out of view
        # capybara is missing support to check wether an element is scrolled into view
        assert not is_in_viewport(page, find('.below_scroll'))
        assert find('.below_scroll').text_content() == 'Visible but scrolled out ouf view'
        # will auto scroll into view
        find('.below_scroll').click()
        assert is_in_viewport(page, find('.below_scroll'))