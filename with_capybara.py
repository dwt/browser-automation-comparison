# https://github.com/elliterate/capybara.py

import capybara
from capybara.dsl import *
from selenium.webdriver.common.keys import Keys

from firefox import find_firefox

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
