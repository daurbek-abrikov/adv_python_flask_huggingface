from flask import Flask, render_template, request, flash
from flask.json import jsonify
from flask_sqlalchemy import SQLAlchemy
from bs4 import BeautifulSoup, re
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from transformers import pipeline
from datetime import datetime, timedelta
import jwt
import time


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:785213@localhost:5432/pythonFlaskDB'
app.config['SECRET_KEY'] = 'thisismyflasksecretkey'

db = SQLAlchemy(app)


def refactoredCoinName(coin): # For example "Binance Coin" -> "binance-coin"
    result = str(coin.lower())
    splittedCoin = result.split()
    if len(splittedCoin) > 1:
      result = str(splittedCoin[0])
      for i in range(1, len(splittedCoin)):
        result += "-" + splittedCoin[i]
    return result


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/login', methods=['POST'])
def login():
    login = request.form.get('login')
    password = request.form.get('password')

    user = User.query.filter_by(login=login).first() 

    if user:
        user_login = User.query.filter_by(login=login).first().login 
        user_pass = User.query.filter_by(login=login).first().password 

        if user_login==login and user_pass==password:
            token = jwt.encode({'user': login, 'exp':datetime.utcnow() + timedelta(minutes=30)}, app.config['SECRET_KEY'])

            user.token = token
            db.session.add(user)
            db.session.commit()
            return jsonify({'token': token})  
 
    flash('Please check your login details and try again.')
    return render_template('login.html')


@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')


@app.route('/news', methods=['POST'])
def find_coin_news():
    coin_name = refactoredCoinName(request.form.get('coin_name'))

    res = News.query.filter_by(coin=coin_name).all() 

    if not res:
        URL = "https://coinmarketcap.com/currencies/" + coin_name +"/news/"
        opts = webdriver.ChromeOptions()
        opts.headless =True
        opts.add_argument("--enable-javascript")
        opts.add_experimental_option("prefs", {"profile.default_content_setting_values.cookies": 2})
        
        browser = webdriver.Chrome(ChromeDriverManager().install(), options=opts)
        r = browser.get(URL)
        
        summarizer = pipeline("summarization")
        button = browser.find_elements_by_xpath("//button[text()='Load More']")

        for i in range(3):
            button[0].click()
            time.sleep(3)
        
        news = browser.find_elements_by_xpath("//main//a")
        news_links = [n.get_attribute("href") for n in news] 

        for i in  range(0, len(news_links)):
            link = news_links[i]
            r = browser.get(link)
            
            soup = BeautifulSoup(browser.page_source, 'html.parser')


            p_list = browser.find_all('p')
            p_text = [p.text for p in p_list]
            ARTICLE = ' '.join(p_text)
            
            SUM = summarizer(ARTICLE, max_length=75, min_length=60, do_sample=False)
            sum = ' '.join([summ['summary_text'] for summ in SUM])
            news = News(coin=coin_name, paragraph=ARTICLE, summary=sum)
            db.session.add(news)
        db.session.commit()

        res = News.query.filter_by(coin=coin_name).all()
        return render_template('news.html', results=res)
    
    return render_template('news.html', results=res)
    

@app.route('/news', methods=['GET'])
def coin_news():
    return render_template('news.html')


class User(db.Model):
    __tablename__ = 'User'
    id = db.Column('id', db.Integer, primary_key=True)
    login = db.Column('login', db.String(80), unique=True)
    password = db.Column('password', db.String(80))
    token = db.Column('token', db.String)

    def __init__(self, login, password, token):
        self.login = login
        self.password = password
        self.token = token

    def __repr__(self):
        return f"User('{self.login}', '{self.token}')"


class News(db.Model):
    __tablename__ = 'News'
    id = db.Column('id', db.Integer, primary_key=True)
    coin = db.Column('coin', db.String(80))
    paragraph = db.Column('paragraph', db.Text)
    summary = db.Column('summary', db.Text)

    def __init__(self, coin, paragraph, summary):
        self.coin = coin
        self.paragraph = paragraph
        self.summary = summary

    def __repr__(self):
        return f"News('{self.coin}', '{self.paragraph}', '{self.summary}')"


db.drop_all()
db.create_all()

user1 = User(login='first_user', password='password', token='some_token')
user2 = User(login='second_user', password='password', token='some_token')
user3 = User(login='third_user', password='password', token='some_token')

db.session.add(user1)
db.session.add(user2)
db.session.add(user3)

db.session.commit()


if __name__ == "__main__":
    app.run(debug=True)
