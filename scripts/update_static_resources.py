import requests
import pygments.formatters
import shutil

#['fruity', 'perldoc', 'trac', 'native', 'autumn', 'emacs', 'vs',
#'rrt', 'colorful', 'monokai', 'pastie', 'default', 'borland',
#'manni', 'vim', 'bw', 'friendly', 'tango', 'murphy']
PYGMENTS_STYLE = 'tango'
pygments_css = (pygments.formatters.HtmlFormatter(style=PYGMENTS_STYLE)
                .get_style_defs('.codehilite'))
with open('pygments.css', 'w') as f:
    f.write(pygments_css)


def curl(url, file):
    response = requests.get(url, stream=True)
    with open(file, 'wb') as f:
        shutil.copyfileobj(response.raw, f)
        del response


for s in [ 60, 76, 114, 152 ]:
    curl('http://www.gravatar.com/avatar/767447312a2f39bec228c3925e3edf74?s={}'.format(s),
         'redwind/static/img/users/kyle{}.jpg'.format(s))
