# https://github.com/Microsoft/playwright-python
# Does not seem to use selenium? Does not seem to use Webdriver, uses special Browser-Builds instead?
# Does seem to have access to almost all browser behaviour, even stuff that is hard with selenium
# - like downloads, file choosers
# - Can record video of test run
# - can control ajax requests


from playwright.sync_api import sync_playwright

import pytest

HEADLESS = True
# HEADLESS = False

@pytest.fixture
def page():
    with sync_playwright() as playwright:
        browser = playwright.firefox.launch(headless=HEADLESS)
        page = browser.new_page()
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