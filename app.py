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

@app.get('/hidden')
def hidden():
    return '''
    <!doctype html>
    <html>
    <body>
        <span class="visible">Visible because just normal content in the body</span>
        <span class="invisible" style="visibility:hidden">Hidden because visibility:hidden</span>
        <span class="removed" style="display:none">Hidden because display:none</span>
        <span class="out_of_frame" style="position:absolute; left:-100vw">Hidden because moved out of frame</span>
        <div style="position:relative">
            <div class="behind" style="position:absolute; top:0; left:0; width:200px; height:200px">Hidden because behind another div</div>
            <div style="position:absolute; top:0; left:0; width:200px; height:200px; background-color:white">Front</div>
        </div>
        <div class="placeholder" style="height:100vh"></div>
        <span class="below_scroll">Visible but scrolled out ouf view</span>
    </body>
    </html>
    '''

@app.get('/shadow')
def shadow():
    return '''
    <!doctype html>
    <html>
    <head>
        <script>
        customElements.define('labeled-input', 
            class extends HTMLElement {
                connectedCallback() {
                    var shadow = this.attachShadow({mode: this.getAttribute('mode') || 'open' })
                    shadow.innerHTML = `
                        <div>
                        <label>
                            ${ this.getAttribute('label-text') }
                            <input 
                                type="${ this.getAttribute('type') }"
                                name="${ this.getAttribute('name') }"
                            >
                        </label>
                        </div>
                    `
                }
            }
        )
        </script>
    </head>
    <body>
        <labeled-input name=first type=text label-text="First Name"></labeled-input>
        <labeled-input name=last type=text label-text="Last Name" mode=closed></labeled-input>
    </body>
    </html>
    '''