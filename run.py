from app import app
import webbrowser
from flaskwebgui import FlaskUI
gui = FlaskUI(app, width=800, height=600, start_server="flask")

if __name__ == '__main__':
    gui.run()