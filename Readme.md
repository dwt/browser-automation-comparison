# How do current python browser automation frameworks compare?

Current means late 2021, thats when I last looked intensively at this.

## Looking at

- [Selenium](https://www.selenium.dev/selenium/docs/api/py/)
- [Capybara-py](https://github.com/elliterate/capybara.py) (Selenum based)
- [Selene](https://github.com/yashaka/selene) (Selenium based)
- [Splinter](https://github.com/cobrateam/splinter/) (Selenium based )
- [Playwright-python](https://github.com/Microsoft/playwright-python)

## Use cases covered

### Simple google search

- How to do something simple
- What setup is required
- How to get a custom option into the framework (firefox custom executable path)

### Nested selection with dynamically changing dom

- How does the framework deal with dynamicaly changing dom?
- How do nested selects work if parts of the selected dom dissappear midway?

### Form interaction

- How can form fields be adressed? By Label? Placeholder?

### Falling back to basic tools if the framwork doesn't support something

- Plain Selenium (if selenium based)
- JS, can it access a framework selection?

## Comparison criteria

- How simple is it to get going
- How to switch between headless / gui visible
- How to select UI elements by id, css, xpath, title, placeholder, label
    - Especially if I don't care what exactly it is (button/ link), textfield/input/ custom?
- How to express complex search queries (class + text, multiple classes)
- custom wait times
- How to assert information in the page
- How to send return to textfields to trigger form submit handlers
- How to deal with autowaiting? Page did load, js / updating pages, especially with compound search terms (within x, within y, find z)
- Way to traverse (only?) accessibility information, i.e. use AC tests to ensure accessibility interfaces are thourough enough to reach every important input
- How to fall back to selenium for stuff the abstraction library doesn't cover (e.g. drag'n'drop)
- How can test isolation be achieved?
- Can it simulate multiple concurrent browsers?
- How to deal with multiple windows and popups?
- How to handle login / basic authentication
- File up-/download
- drag'n'drop
- alternative runners if js is not required (interesting for speed, local testing of classical apps)
- Is there a speed difference between the frameworks?
- Support for async python
- Error handling
  - Try to interact with offscreen element
  - Try to interact with hidden / invisible elements
  - Try to interact with element behind another element
- touch intereaction

## Further work

- What would be interesting to see? Send pull requestss
