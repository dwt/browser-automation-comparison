import subprocess
import pytest
import re
import atexit
from subprocess import run

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

@pytest.fixture(scope='session')
def flask_uri():
    with subprocess.Popen(['flask', 'run', '--reload'], stderr=subprocess.PIPE, encoding='utf8') as process:
        flask_url = None
        still_starting = True
        while still_starting:
            output = process.stderr.readline()
            match = re.match(r'^.* Running on (http://[\d\.\:]+/).*$', output)
            still_starting = match is None
                
        flask_url = match.group(1)
        
        def kill():
            process.terminate()
            process.wait()
        
        atexit.register(kill)
        
        yield flask_url
        
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
        assert expected_output in output

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
    parser.addoption("--browser", default='all', choices=('all', 'firefox', 'chrome', 'safari'), help="default: all")

def pytest_generate_tests(metafunc):
    if "browser_vendor" in metafunc.fixturenames:
        browser_vendor = [metafunc.config.getoption("browser")]
        if ['all'] == browser_vendor:
            browser_vendor = ['firefox', 'chrome', 'safari']
        metafunc.parametrize("browser_vendor", browser_vendor, scope='session')

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
