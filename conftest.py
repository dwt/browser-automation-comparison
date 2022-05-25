import subprocess
import pytest
import re
import atexit
from subprocess import run

## Locating browsers

def find_firefox():
    return find_application('Firefox')

def find_chrome():
    return find_application('Google Chrome')

def find_application(application_name, executable_name=None):
    find_bundle_command = ['mdfind', f'kMDItemFSName == "{application_name}.app"']
    extract_command = ['plutil', '-extract', 'CFBundleExecutable', 'raw', '-o', '-']
    paths = run(find_bundle_command, capture_output=True).stdout.decode().splitlines()
    
    assert len(paths) > 0
    bundle_path = paths[0].strip()
    info_plist_path = bundle_path + '/Contents/Info.plist'
    if executable_name is None:
        executable_name = run(extract_command + [info_plist_path], capture_output=True).stdout.decode().splitlines()[0]
    return bundle_path + '/Contents/MacOS/' + executable_name

## Interacting with Flask

@pytest.fixture(scope='session')
def flask_uri(browser_vendor):
    with subprocess.Popen(['flask', 'run', '--reload'], stderr=subprocess.PIPE, encoding='utf8') as process:
        flask_url = None
        still_starting = True
        while still_starting:
            output = process.stderr.readline()
            match = re.match(r'^.* Running on (http://[\d\.\:]+).*$', output)
            still_starting = match is None
                
        flask_url = match.group(1)
        
        @atexit.register
        def kill():
            process.terminate()
            process.wait()
        
        if 'remote-' not in browser_vendor:
            yield flask_url
        else:
            protocol, host, port = flask_url.split(':')
            yield ':'.join([protocol, '//host.docker.internal', port])
        
        kill()

def add_auth_to_uri(uri, username, password):
    import urllib
    parse_result = urllib.parse.urlparse(uri)
    parse_result_with_auth = urllib.parse.ParseResult(parse_result[0], f'{username}:{password}@' + parse_result[1], *parse_result[2:])
    return parse_result_with_auth.geturl()

@pytest.fixture
def ask_to_leave_script():
    return '''
        // interestingly Firefox webdriver doesn't show thes dialogs at all, even though this code works in normal Firefox
        window.addEventListener('beforeunload', function (e) {
            // Cancel the event
            e.preventDefault(); // mozilla will now always show dialog
            // Chrome requires returnValue to be set
            e.returnValue = 'Fnord';
        });
    '''

@pytest.fixture
def force_open_shadow_dom_script():
    return '''
    var original = Element.prototype.attachShadow
    Element.prototype.attachShadow = function(config) {
        config.mode = 'open'
        return original.apply(this, arguments)
    }
    '''

## Test helpers and assertions

# Selenium style xpath matcher
@pytest.fixture
def xpath():
    class XPath:
        def __getattr__(self, name):
            from xpath import html
            from xpath.renderer import to_xpath
            
            def callable(*args, **kwargs):
                return to_xpath(getattr(html, name)(*args, **kwargs))
            
            return callable
    
    return XPath()


def assert_is_png(path):
    assert_is_file(path, '.png', b'PNG image data', b'8-bit/color RGBA, non-interlaced')

def assert_is_file(path, expected_suffix, *expected_file_outputs):
    assert path.exists() and path.is_file()
    assert path.stat().st_size > 1000
    assert path.suffix == expected_suffix
    
    import subprocess
    output = subprocess.check_output(['file', path])
    for expected_output in expected_file_outputs:
        assert re.search(expected_output, output)

from contextlib import contextmanager
from datetime import datetime
@contextmanager
def assert_no_slower_than(seconds=1):
    before = datetime.now()
    yield
    after = datetime.now()
    assert (after - before).total_seconds() < seconds

## pytest customization to add multi browser support

def pytest_addoption(parser):
    parser.addoption("--browser", default='all', help="default: all (local browsers)", choices=(
        'all', 'firefox', 'chrome', 'safari', 'remote-selenium', 'remote-playwright'
    ))
    parser.addoption("--headless", default=False, action='store_true', help='default: false')

def pytest_generate_tests(metafunc):
    if "browser_vendor" in metafunc.fixturenames:
        browser_vendor = [metafunc.config.getoption("browser")]
        if ['all'] == browser_vendor:
            browser_vendor = ['firefox', 'chrome', 'safari']
        metafunc.parametrize("browser_vendor", browser_vendor, scope='session')

@pytest.fixture(scope='session')
def is_headless(request):
    return request.config.getoption('headless')

# xfail or skipif don't have access to fixture arguments
# also skipif is evaluated before the fixture, which means the side effect of the fixture cannot be used
# Thus special implementation is needed to graft this functionality on top of pytest
# inspired by https://stackoverflow.com/questions/28179026/how-to-skip-a-pytest-using-an-external-fixture
# This has the unfortunate side effect of forcing each test to be parametrized by browser vendor. 
# Not a problem if that is required / wanted anyway, but not super nice.
@pytest.fixture(autouse=True)
def skip_or_xfail_safari(request, browser_vendor):
    if 'safari' != browser_vendor:
        return
    
    def reason(marker_name):
        return request.node.get_closest_marker(marker_name).kwargs['reason']
    
    if request.node.get_closest_marker('xfail_safari'):
        # add a normal xfail marker, to allow the test to execute
        request.node.add_marker(pytest.mark.xfail(reason=reason('xfail_safari')))
        
    if request.node.get_closest_marker('skipif_safari'):
        return pytest.skip(msg=reason('skipif_safari'))


def run_selenium_in_docker_if_neccessary(browser_vendor, docker_compose_target):
    if 'remote-selenium' != browser_vendor:
        yield
        return
    
    import subprocess
    import requests
    import time
    
    def selenium_grid_is_up():
        try:
            return requests.get('http://localhost:4444/wd/hub/status').json()['value']['ready']
        except requests.ConnectionError:
            return False
    
    def wait_for_selenium_grid():
        while not selenium_grid_is_up():
            time.sleep(.2)
    
    subprocess.run(['docker', 'compose', 'up', '-d', docker_compose_target])
    wait_for_selenium_grid()
    try:
        yield
    finally:
        # stopping `docker compose` gracefully via signals doesn't seem to work at all
        # especially SIGTERM should have worked, as that is what gets sent on ctrl-c
        subprocess.run(['docker', 'compose', 'stop', docker_compose_target])

@pytest.fixture(scope='session')
def run_selenium_firefox_in_docker_if_neccessary(browser_vendor):
    yield from run_selenium_in_docker_if_neccessary(browser_vendor, 'selenium-firefox')

@pytest.fixture(scope='session')
def run_selenium_chrome_in_docker_if_neccessary(browser_vendor):
    yield from run_selenium_in_docker_if_neccessary(browser_vendor, 'selenium-chrome')

@pytest.fixture(scope='session')
def run_playwright_chrome_in_docker_if_neccessary(browser_vendor):
    if 'remote-playwright' != browser_vendor:
        yield
        return
    
    with subprocess.Popen(
        ['docker', 'compose', 'run', '--service-ports', 'playwright-remote'], 
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf8'
    ) as process:
        @atexit.register
        def kill():
            process.terminate()
            process.wait()

        playwright_url = None
        still_starting = True
        while still_starting:
            output = process.stdout.readline()
            print(f'{output=}')
            # example ws://127.0.0.1:2342/143c3727b691bceeb8bbeb349715452c
            match = re.match(r'^.*(ws://[\d\.\:]+/\w+).*$', output)
            still_starting = match is None
    
    playwright_url = match.group(1)
    print(f'{playwright_url=}')
    
    try:
        from collections import namedtuple
        CDP = namedtuple('ChromeDevToolProtocol', ['url'])
        yield CDP(url=playwright_url)
    finally:
        subprocess.run(['docker', 'compose', 'stop', 'playwright-remote'])
        kill()
        