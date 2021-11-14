# How do current python browser automation frameworks compare?

Current means late 2021, thats when I last looked intensively at this.

## Looking at

- [Selenium](https://www.selenium.dev/selenium/docs/api/py/)
- [Capybara-py](https://github.com/elliterate/capybara.py) (Selenum based)
- [Selene](https://github.com/yashaka/selene) (Selenium based)
- [Splinter](https://github.com/cobrateam/splinter/) (Selenium based )
- [Playwright-python](https://github.com/Microsoft/playwright-python)

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

## Further work
- What would be interesting to see?
