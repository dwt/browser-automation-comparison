import subprocess
import pytest
import re
import atexit
from subprocess import run

def find_firefox():
    paths = run(['mdfind', 'kMDItemFSName == Firefox.app'], capture_output=True).stdout.splitlines()
    assert len(paths) > 0
    return paths[0].strip().decode() + '/Contents/MacOS/firefox'

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
