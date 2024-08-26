import re
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import mysql.connector
import pickle
import numpy as np
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "your-secret-key-here"

# Load models and data using context managers
def load_data(file_name):
    with open(file_name, 'rb') as file:
        return pickle.load(file)

pt = load_data('models/pt.pkl')
final_ratings = load_data('models/final_ratings.pkl')  # assuming this file exists and is structured correctly
popular_df = load_data('models/popular.pkl')
similarity_scores = load_data('models/similarity_scores.pkl')

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
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['username'] = user['name']
            return redirect(url_for('index'))
        return render_template('login.html', error='Invalid email or password')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        if not is_valid_name(name):
            return render_template('signup.html', error='Invalid name. Please enter a valid name.')
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return render_template('signup.html', error='Email already exists')
        cursor.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (name, email, password))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('login'))
    return render_template('signup.html')

def is_valid_name(name):
    return bool(re.match("^[a-zA-Z ]+$", name))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/recommend')
def recommend_ui():
    return render_template('recommend.html')


# def recommend(book_title):
#     if book_title not in pt.index:
#         print("Book not found in the dataset.")
#         return []
#
#     idx = np.where(pt.index == book_title)[0][0]
#     scores = list(enumerate(similarity_scores[idx]))
#     sorted_scores = sorted(scores, key=lambda x: x[1], reverse=True)
#
#     similar_books = []
#     book_author = final_ratings[final_ratings['Book-Title'] == book_title]['Book-Author'].iloc[0]
#     for i, score in sorted_scores:
#         title = pt.index[i]
#         author = final_ratings[final_ratings['Book-Title'] == title]['Book-Author'].iloc[0]
#         image = final_ratings[final_ratings['Book-Title'] == title]['Image-URL-M'].iloc[0]
#
#         # Fetch the average rating from popular_df
#         avg_rating = popular_df[popular_df['Book-Title'] == title]['avg_rating'].iloc[0] if title in popular_df[
#             'Book-Title'].values else  avg_rating == avg_rating
#
#         if author == book_author:
#             similar_books.append((title, author, image, avg_rating, score))
#         if len(similar_books) == 5:
#             break
#
#     return similar_books
def recommend(book_title):
    if book_title not in pt.index:
        print("Book not found in the dataset.")
        return []

    idx = np.where(pt.index == book_title)[0][0]
    scores = list(enumerate(similarity_scores[idx]))
    sorted_scores = sorted(scores, key=lambda x: x[1], reverse=True)

    similar_books = []
    book_author = final_ratings[final_ratings['Book-Title'] == book_title]['Book-Author'].iloc[0]
    for i, score in sorted_scores:
        title = pt.index[i]
        author = final_ratings[final_ratings['Book-Title'] == title]['Book-Author'].iloc[0]
        image = final_ratings[final_ratings['Book-Title'] == title]['Image-URL-M'].iloc[0]

        # Fetch the average rating from popular_df
        avg_rating = popular_df[popular_df['Book-Title'] == title]['avg_rating'].iloc[0] if title in popular_df[
            'Book-Title'].values else "0"

        if author == book_author:
            similar_books.append((title, author, image, avg_rating, score))
        if len(similar_books) == 5:
            break

    return similar_books


@app.route('/get_recommendations', methods=['POST'])
def get_recommendations():
    if not request.form.get('book_title'):
        return jsonify({'message': 'No book title provided'}), 400  # Ensure book title is provided

    book_title = request.form.get('book_title')
    recommendations = recommend(book_title)
    if recommendations:
        return jsonify({'data': recommendations})
    else:
        return jsonify({'message': 'No recommendations found.'})

if __name__ == '__main__':
    app.run(debug=True, port=2024)
