import re

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import mysql.connector
import pickle
import numpy as np

# Load models and data
popular_df = pickle.load(open('models/popular.pkl', 'rb'))
pt = pickle.load(open('models/pt.pkl', 'rb'))
books = pickle.load(open('models/books.pkl', 'rb'))
similarity_scores = pickle.load(open('models/similarity_scores.pkl', 'rb'))

app = Flask(__name__)
app.secret_key = "dgjrywtaygy465fggs"

# MySQL configurations
mysql_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'book_recommendation_system'
}

@app.route('/')
def index():
    if 'username' in session:

        return render_template('index.html',
                               book_name=list(popular_df['Book-Title'].values),
                               author=list(popular_df['Book-Author'].values),
                               image=list(popular_df['Image-URL-M'].values),
                               votes=list(popular_df['num_ratings'].values),
                               rating=list(popular_df['avg_rating'].values))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session['username'] = user['name']
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Sorry Invalid email or password')

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        # Check if the name is valid
        if not is_valid_name(name):
            return render_template('signup.html', error='Invalid name. Please enter a valid name.')

        # Check if email already exists
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        if user:
            cursor.close()
            conn.close()
            return render_template('signup.html', error='Email already exists')

        # Insert user into database
        cursor.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (name, email, password))
        conn.commit()
        cursor.close()
        conn.close()

        # session['username'] = name
        return redirect(url_for('login'))
    return render_template('signup.html')

def is_valid_name(name):
    # Add your validation logic here, for example:
    # Name should contain only alphabets and spaces
    return bool(re.match("^[a-zA-Z ]+$", name))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/recommend')
def recommend_ui():
    return render_template('recommend.html')


@app.route('/recommend_books', methods=['POST'])
def recommend():
    user_input = request.form.get('user_input')
    try:
        index = np.where(pt.index == user_input)[0][0]
        similar_items = sorted(list(enumerate(similarity_scores[index])), key=lambda x: x[1], reverse=True)[1:5]

        data = []
        for i in similar_items:
            item = []
            temp_df = books[books['Book-Title'] == pt.index[i[0]]]
            item.extend(list(temp_df.drop_duplicates('Book-Title')['Book-Title'].values))
            item.extend(list(temp_df.drop_duplicates('Book-Title')['Book-Author'].values))
            item.extend(list(temp_df.drop_duplicates('Book-Title')['Image-URL-M'].values))

            data.append(item)

        if not data:
            return render_template('recommend.html', data=None, message="Not exist in the training dataset, the system cannot find similar books.")

        return render_template('recommend.html', data=data)

    except IndexError:
        return render_template('recommend.html', data=None, message="Not exist in the training dataset, the system cannot find similar books.")


if __name__ == '__main__':
    app.run(debug=True)
