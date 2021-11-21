# https://github.com/cobrateam/splinter/

from pathlib import Path

from selenium.webdriver.firefox.options import Options
from splinter import Browser
from firefox import find_firefox
from conftest import assert_is_png

import pytest

HEADLESS = True
# HEADLESS = False

@pytest.fixture
def browser():
    options = Options()
    options.binary = find_firefox()
    options.headless = HEADLESS

    with Browser('firefox', options=options) as browser:
        yield browser
        browser.quit()

def test_google(browser):
    """
    - nicely short
    - searching is low level
    - no explicit waiting. Nice!
    """
    
    browser.visit('https://google.com')
    browser.find_by_text("Ich stimme zu").click()
    
    browser.find_by_css('[title=Suche]').fill('Selenium')
    browser.find_by_css('[value="Google Suche"]').click()
    
    assert len(browser.find_by_css('.g')) >= 10
    assert browser.is_text_present("Selenium automates browsers")

def test_nested_select_with_retry(browser, flask_uri):
    """
    - can do nested searches
    - but not mixed with matchers, those can only be done on browser
    - There seems to be no API suppport to express complex matchers (i.e. this class AND that text)
    - Of course can write them as xpath if I really need to...
    """
    browser.visit(flask_uri + '/dynamic_disclose')
    browser.find_by_text("Trigger").click()
    browser.is_text_present('fnord')
    inner = browser.find_by_css('#outer').find_by_css('#inner')
    assert 'fnord' in inner.text

def by_label(label_text):
    # could use xpath library from capybara
    return (
        f'//input[@id = //label[contains(string(.), "{label_text}")]/@for]'
        f' | //label[contains(string(.), "{label_text}")]//input'
    )

def test_fill_form(browser, flask_uri):
    """
    - no native way to find by label
    """
    browser.visit(flask_uri + '/form')
    browser.find_by_xpath(by_label('First name')).fill('Martin')
    browser.find_by_xpath(by_label('Last name')).fill('Häcker')
    browser.find_by_css('[placeholder="your@email"]').fill('foo@bar.org')
    
    assert 'Martin' == browser.find_by_css('#first_name').value
    assert 'Häcker' == browser.find_by_css('#last_name').value
    assert 'foo@bar.org' == browser.find_by_css('#email').value

def locate_by_js(browser, element, js):
    "Provides the element under the name 'element' to js"
    unwrapped_element = browser.execute_script('const element = arguments[0];' + js, element._element)
    
    from splinter.driver.webdriver import WebDriverElement
    return WebDriverElement(unwrapped_element, element)

def test_fallback_to_selenium_and_js(browser, flask_uri):
    """
    - not easy to find elements by js
    """
    browser.visit(flask_uri + '/form')
    element = browser.find_by_xpath(by_label('First name')).first
    
    selenium_element = element._element
    from selenium.webdriver.remote.webelement import WebElement
    assert isinstance(selenium_element, WebElement)
    
    selenium_element.send_keys('fnord')
    assert element.value == 'fnord'
    
    assert browser.evaluate_script('1+1') == 2
    assert locate_by_js(browser, element, 'return element.parentElement').tag_name == 'form'

def test_select_by_different_criteria(browser, flask_uri, xpath):
    """
    - api support is _very_ basic.
    - xpath library integration works. At leas there is that
    """
    browser.visit(flask_uri + '/selector_playground')
    
    def assert_field(element):
        assert element.value == 'input_value'
    
    assert_field(browser.find_by_css('.input_class'))
    assert_field(browser.find_by_xpath('//*[@placeholder="input_placeholder"]'))
    assert_field(browser.find_by_name('input_name'))
    assert_field(browser.find_by_tag('input'))
    assert_field(browser.find_by_value('input_value'))
    assert_field(browser.find_by_id('input_id'))
    # find_by_text not applicable
    
    # Aria - no special support
    
    # Complex criteria - no support, possible via css and xpath
    assert_field(browser.find_by_css('[placeholder=input_placeholder][name=input_name]'))
    assert_field(browser.find_by_xpath('//*[@placeholder="input_placeholder"][@name="input_name"]'))
    
    # xpath selector libraries easy to use
    assert_field(browser.find_by_xpath(xpath.field('input_label')))

def test_debugging_support(browser, flask_uri, tmp_path):
    """
    - nothing special, nothign unexpected
    - also doesn't seem to make a distinction between html attributes and js properties
    """
    browser.visit(flask_uri + '/selector_playground')
    
    # get html of page
    assert '<label for' in browser.html
    # get html of a selection
    field = browser.find_by_xpath('//input')
    assert field['outerHTML'].startswith('<input id=')
    
    
    # get screenshot of page
    path = tmp_path / 'full_screenshot'
    # strangely splinter expects a 'filename' to which it then appends some random stuff
    # Other APIs either allow you to set an explicit path, or create the whole path randomly
    actual_path = browser.screenshot(path.as_posix())
    assert_is_png(Path(actual_path))
    
    