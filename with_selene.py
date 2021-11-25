# https://github.com/yashaka/selene

from selene import by, be, have, query
from conftest import find_firefox, assert_is_png

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

def by_label(label_text):
    # could use xpath library from capybara
    return by.xpath(
        f'//input[@id = //label[contains(string(.), "{label_text}")]/@for]'
        f' | //label[contains(string(.), "{label_text}")]//input'
    )

def test_fill_form(browser, flask_uri):
    """
    - no native way to select inputs by label
    """
    browser.open(flask_uri + '/form')
    browser.element(by_label('First name')).type('Martin')
    browser.element(by_label('Last name')).type('Häcker')
    browser.element(by.css('[placeholder="your@email"]')).type('foo@bar.org')
    
    assert 'Martin' == browser.element(by.css('#first_name')).get(query.attribute('value'))
    assert 'Häcker' == browser.element(by.css('#last_name')).get(query.attribute('value'))
    assert 'foo@bar.org' == browser.element(by.css('#email')).get(query.attribute('value'))

def locate_by_js(element, js):
    "Provides the element under the name 'element' to js"
    unwrapped_element = element.execute_script('const element = arguments[0];' + js)
    from selenium.webdriver.remote.webelement import WebElement
    assert isinstance(unwrapped_element, WebElement)
    
    from selene.core.entity import Element, Locator
    return Element(Locator(f'{element}.execute_script()', lambda: unwrapped_element), element.config)

def test_fallback_to_selenium_and_js(browser, flask_uri):
    """
    - accessing the underlying selenium element is easy
    - locating via js is not really supported
    """
    browser.open(flask_uri + '/form')
    
    selenium_browser = browser.config.driver
    from selenium import webdriver
    assert isinstance(selenium_browser, webdriver.Firefox)

    element = browser.element(by_label('First name'))
    
    from selenium.webdriver.remote.webelement import WebElement
    assert isinstance(element(), WebElement)
    
    element().send_keys('fnord')
    assert element.get(query.attribute('value')) == 'fnord'
    
    # Can even return the correct wrapper element for dom references!
    assert element.execute_script('return 1+1') == 2
    
    # selection via js is possible, but needs manual re-wrapping in selene
    parent = locate_by_js(element, 'return element.parentElement')
    assert parent.tag_name == 'form'

def test_select_by_different_criteria(browser, flask_uri, xpath):
    """
    - Selection is rather limited if you don't want to fall back to css / xpath constantly
    - at least this allows integrating selection libraries like xpath.py
    """
    browser.open(flask_uri + '/selector_playground')
    
    def assert_field(*args, **kwargs):
        browser.element(*args, **kwargs).should(have.attribute('id', 'input_id'))
    
    assert_field(by.css('[title=input_title'))
    assert_field(by.id('input_id'))
    assert_field(by.name('input_name'))
    assert_field(by.xpath('//*[@placeholder="input_placeholder"]'))
    # by.link_text, by.partial_link_text, by.partial_text, by.text not applicable
    
    # no special support for Aria
    
    # Complex criteria, no special support, can be approximated by concatenating xpath or css conditions
    assert_field(by.xpath('//*[@id="input_id"][@placeholder="input_placeholder"]'))
    assert_field(by.css('[id="input_id"][placeholder="input_placeholder"]'))
    
    assert_field(by.xpath(xpath.field('input_label')))

def test_debugging_support(browser, flask_uri, tmp_path):
    """
    - basic support, nothing surprising
    - nice that it has outer_html in it's api
    """
    browser.open(flask_uri + '/selector_playground')
    field = browser.element(by.css('input'))
    
    # get html of page
    assert '<label for' in browser.element('html').get(query.outer_html)
    # there is also browser.save_page_source(path)
    
    # get html of a selection
    assert field.get(query.outer_html).startswith('<input id=')
    
    # get screenshot of page
    path = tmp_path / 'full_screenshot.png'
    browser.save_screenshot(path.as_posix()) # doesn't accept pathlib paths!
    assert_is_png(path)
    # can generate filenames and has browser.last_screenshot() to get that path later
