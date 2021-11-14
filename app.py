from flask import Flask

app = Flask(__name__)

@app.route("/dynamic_disclose")
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
