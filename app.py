import functools

import flask

app = flask.Flask(__name__)

@app.get('/')
def index():
    return flask.redirect('/selector_playground')

@app.get("/dynamic_disclose")
def dynamic_disclosure():
    return '''
    <div id=container>
        <div id=outer>
            Container
            <div id=inner>
            </div>
        </div>
    </div>
    <button onclick=trigger()>Trigger</button>
    <script>
    function trigger() {
        div = document.querySelectorAll('#container')[0]
        setTimeout(function() {
            div.innerHTML = "<div id=outer><div id=inner>fnord</div></div>"
        }, 1000)
    }
    </script>
    '''

@app.get('/form')
def form():
    return '''
    <form>
        <label for=first_name>First name:</label><input id=first_name>
        <label>Last name:<input id=last_name></label>
        <input id=email placeholder=your@email>
    </form>
    '''

@app.get('/selector_playground')
def selector_playground():
    return '''
    <form>
        <label for=input_id id=label>input_label</label>
        <input id=input_id class=input_class name=input_name value=input_value 
            title=input_title placeholder=input_placeholder aria-label=input_aria_label>
        <div id=div_id>div_text</div>
    </form>
    '''

def is_correct_auth(username, password):
    return username == 'admin' and password == 'password'

def authenticate():
    response = flask.make_response("You need to authenticate")
    response.status_code = 401
    response.headers['WWW-Authenticate'] = 'Basic realm="Main"'
    return response

def requires_basic_auth(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        auth = flask.request.authorization
        if not auth or not is_correct_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.get('/basic_auth')
@requires_basic_auth
def basic_auth():
    return 'Authenticated'
