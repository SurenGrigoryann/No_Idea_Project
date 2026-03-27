from flask import Flask, redirect, url_for
from progress_test import progress_bp
from home import home_bp
 
app = Flask(__name__)
app.secret_key = "change-this-to-a-secure-random-key"
 
app.register_blueprint(home_bp, url_prefix='/home')
app.register_blueprint(progress_bp)
 
@app.route("/")
def index():
    return redirect(url_for("home.home"))
 
if __name__ == "__main__":
    app.run(debug=True)
 