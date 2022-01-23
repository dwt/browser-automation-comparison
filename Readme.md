# How do current python browser automation frameworks compare?

Current means late 2021, thats when I last looked intensively at this.

## Looking at

- [Selenium](https://www.selenium.dev/selenium/docs/api/py/)
- [Capybara-py](https://github.com/elliterate/capybara.py) (Selenum based)
- [Selene](https://github.com/yashaka/selene) (Selenium based)
- [Splinter](https://github.com/cobrateam/splinter/) (Selenium based )
- [Playwright-python](https://github.com/Microsoft/playwright-python)

## How to execute the tests

    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    python -m playwright install
    pytest

## Use cases cosvered

1. Simple google search
    - How to do something simple
    - What setup is required
    - How to get a custom option into the framework (firefox custom executable path)

1. Nested selection with dynamically changing dom
    - How does the framework deal with dynamicaly changing dom?
    - How do nested selects work if parts of the selected dom dissappear midway?

1. Form interaction
    - How can form fields be adressed? By Label? Placeholder?

1. Falling back to basic tools if the framwork doesn't support something
    - Plain Selenium (if selenium based)
    - JS, can it access a framework selection?
    - JS, can I select dom nodes with it?

1. What different ways does the framework support to select stuff on the page
    - What conveniences are provided besides plain css and xpath?

1. What debugging support do the frameworks offer?
    - get html
    - get screenshots
    - get videos
    - get har (http archive) or other logs

1. How do Frameworks support Test-Isolation?
    - cookies
    - {local,session}Storage
    - extra windows
    - open dialogs
    - onbeforeclose handlers

1. How do frameworks deal with dialogs and windows?
    - dialogs (alert, confirm, basic auth password)
        - Basic auth ist often used to lock away staging/ci systems at the proxy level. That is secure, as long as these systems are https only
    - new windows / tabs
    - file uploads
    - onBeforeUnload warning

1. How do frameworks deal with multiple browsers
    - to support multiple concurrent logins
    - possibly for realtime interactions like chat

1. How do frameworks deal with basic authentication?
    - Many staging/testing systems are protected with basic authentication because that is easy to configure at the proxy level without changing the application.

1. How do frameworks deal with hidden elements?
    - display:none, visibility:hidden, moved out of frame, behind other elements, scrolled out of the viewport

1. How different is the API for different browsers?

1. How to Docker?
    - How difficult is it to execute tests in Docker / CI/CD Environments
    - Can tests be observed? Headfull-Execution, Screencasts, Screenshots, VNC?

## Comparison criteria

- how easy to run in docker container? (how to observe? GUI likely not possible, just screenshots, screencasts?)
    - https://github.com/SeleniumHQ/docker-selenium
    - https://hub.docker.com/_/microsoft-playwright
- test mobile / touch interfaes
- How to send return to textfields to trigger form submit handlers
- Way to traverse (only?) accessibility information, i.e. use AC tests to ensure accessibility interfaces are thourough enough to reach every important input
- File up-/download
- how to handle uploads, downloads
- drag'n'drop
- hover
- Support for async python (might be that playwright supports running multiple browsers in parallel this way)
- help() and repr() output, how helpfull is it?, how discoverable is the library interactively?
- can private browsing mode be accessed?
- selene library to auto download drivers / browsers
- test upload, download
- are console messages in scope?

## Further work

- What would be interesting to see? Send pull requestss
- Try out playwrigth record mode
- selene supposedly can download it's own drivers, how does that work?
- how does execution in containers work? How to debug failing tests?
- What differentiates playwright from selenium? What features set it apart?
- How to interact with the page via keyboard shortcuts
- check how easy it is to switch to chromium, safari