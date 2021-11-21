# https://github.com/elliterate/capybara.py

import re

import capybara
from capybara.dsl import *
from selenium.webdriver.common.keys import Keys

from firefox import find_firefox
from conftest import assert_is_png

HEADLESS = True
# HEADLESS = False

@capybara.register_driver("selenium")
def init_selenium_driver(app):
    
    from selenium.webdriver.firefox.options import Options
    options = Options()
    options.binary = find_firefox()
    options.headless = HEADLESS
    
    from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
    
    capabilities = DesiredCapabilities.FIREFOX.copy()
    capabilities["marionette"] = True
    
    from capybara.selenium.driver import Driver
    
    return Driver(app, browser="firefox", options=options, desired_capabilities=capabilities)


capybara.default_driver = "selenium"
capybara.default_max_wait_time = 5

def test_google():
    """
    - Complicated setup to set custom firefox path
    - pretty much the original seleinum api. Nice!
    - lots of warnings
    """
    
    visit("https://google.com")
    click_button('Ich stimme zu')
    fill_in(title='Suche', value='Selenium')
    # sadly doesn't return the found object, so no chaining
    # .send_keys(Keys.RETURN)
    # looks more like a bug than intention
    
    # There are two buttons, though technically only one of them should be visible
    click_button('Google Suche', match='first')
    
    assert len(find_all('.g')) >= 10
    assert has_selector('.g', text='Selenium automates browsers')
    
    capybara.reset_sessions()

def test_nested_select_with_retry(flask_uri):
    """
    - nested searching just works. Ah the joy.
    - expressive find() is a joy to use
    """
    visit(flask_uri + '/dynamic_disclose')
    click_on('Trigger')  # Don't care wether it's a link or button
    inner = find('#outer').find('#inner', text='fnord')
    assert 'fnord' in inner.text

def test_fill_form(flask_uri):
    """
    - as does searching by label or placeholder
    """
    visit(flask_uri + '/form')
    fill_in('First name', value='Martin')
    fill_in('Last name', value='Häcker')
    fill_in('your@email', value='foo@bar.org')
    
    assert 'Martin' == find_field('First name').value
    assert 'Häcker' == find_field('Last name').value
    assert 'foo@bar.org' == find_field('your@email').value

def test_fallback_to_selenium_and_js(flask_uri):
    """
    - simple escaping to selenium
    - simple access to the selected dom node from js
    - wraps returned dom nodes into the native element
    """
    visit(flask_uri + '/form')
    element = find_field('First name')
    
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
    visit(flask_uri + '/selector_playground')
    
    def assert_field(*args, **kwargs):
        assert find_field(*args, **kwargs).value == 'input_value'
    
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
    visit(flask_uri + '/selector_playground')
    field = find_field('input_name')
    
    # get html of page
    assert '<label for' in page.html
    # get html of a selection
    assert field['outerHTML'].startswith('<input id=')
    
    # get screenshot of page
    path = tmp_path / 'full_screenshot.png'
    page.save_screenshot(path)
    assert_is_png(path)

