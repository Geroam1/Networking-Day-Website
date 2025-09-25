from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/test")
def test():
    return render_template("test.html")

@app.route('/companies')
def companies():
    return render_template('companies.html')

@app.route('/students')
def students():
    return render_template('students.html')

if __name__ == "__main__":
    app.run()