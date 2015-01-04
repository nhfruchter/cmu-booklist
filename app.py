from flask import Flask, render_template, url_for, flash, request, redirect, Response
from flask_sslify import SSLify

import booklist 

app = Flask(__name__)
sslify = SSLify(app)

app.config.update({
    'SECRET_KEY': '78b42884271e9fdb2ae42111d636505d',
    'mapping': booklist.get_mapping(6668)
})

@app.route('/')
def home():
    return render_template('home.html')
    
@app.route('/books', methods=['POST'])
def fetch_books():
    cids = request.form.getlist('cids')

    if cids and len(cids) > 0 and cids[0] != '':
        bookinfo = booklist.get_books(app.config['mapping'], cids)
        return view_books(bookinfo)
    else:
        flash("You didn't specify any courses.")
        return redirect(url_for('home'))
            
def view_books(info):
    return render_template('view_books.html', info=info)
    
if __name__ == '__main__':
    app.run(debug=True)