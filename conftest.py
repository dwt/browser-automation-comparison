import subprocess
import pytest
import re
import atexit

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
    assert path.exists() and path.is_file()
    assert path.stat().st_size > 1000
    import subprocess
    output = subprocess.check_output(['file', path])
    assert b'PNG image data' in output
    assert b'8-bit/color RGBA, non-interlaced' in output
