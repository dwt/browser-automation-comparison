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
        
        # FIXME when tests are killed, sometimes it takes longer to actually kill flask in the background
        # Can be so long that the next startup fails because the port is not free
        def kill():
            process.kill()
            process.wait()
        
        atexit.register(kill)
        
        yield flask_url
        
        kill()
        
    
    
