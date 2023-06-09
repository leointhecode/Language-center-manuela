import os
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm
from flask_gravatar import Gravatar
from functools import wraps

#USE OF ENV VAR

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("FLASK_SECRET_KEY")
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///blog.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

#LOGIN MANAGER 

login_manager = LoginManager()
login_manager.init_app(app)

##CONFIGURE TABLES

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))

    posts = relationship("BlogPost", back_populates="author")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")

    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)



with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()


def admin_only(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        if current_user.id == 1:
            return f(*args, **kwargs)
        return abort(403)
    return decorator


@app.route('/')
def get_all_posts():
    
    posts = BlogPost.query.all()
    
    return render_template("index.html", all_posts=posts)

@app.route('/register', methods=['GET', 'POST'])
def register():
    
    form = RegisterForm()
    
    if form.validate_on_submit():
        
        name = form.name.data
        email = form.email.data
        
        hashed_password = generate_password_hash(password=form.password.data,
                                          method='pbkdf2:sha256',
                                          salt_length=10)
        
        user = User.query.filter_by(email=email).first()
        check_name = User.query.filter_by(name=name).first()
        
        print(f" check name = {check_name}")

        if not user:
            if not check_name:
        
                 new_user = User(
                     name=name,
                     email=email,
                     password= hashed_password
                 )

                 db.session.add(new_user)
                 db.session.commit()

                 login_user(new_user)

                 return redirect(url_for("get_all_posts"))
            else:
                flash('That name is already taken.')
            return redirect(url_for("register"))
         
         
        else:
            flash('You have already registered with that email, please try login')
            return redirect(url_for("register"))
            
        
    return render_template("register.html", form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    
    form = LoginForm()
    
    if form.validate_on_submit():
        
        email = form.email.data
        password = form.password.data
        
        user =  User.query.filter_by(email=email).first()
        
        if user:
            if check_password_hash(user.password, password):
                
                login_user(user)
                
                return redirect(url_for("get_all_posts") )
            else:
                flash('The password does not match the email, please try again')
            return redirect(url_for("login"))
        else:
            flash('This email does not exist, please try again')
            return redirect(url_for("login"))
    
    return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=['GET', 'POST'])
def show_post(post_id):

    requested_post = BlogPost.query.get(post_id)

    return render_template("post.html", post=requested_post)


@app.route("/new-post", methods=['GET', 'POST'])
@login_required
@admin_only 
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", methods=['GET', 'POST'])
@login_required
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>", methods=['GET', 'POST'])
@login_required
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))
    

if __name__ == "__main__":

    app.run(host='0.0.0.0', port=9999, debug=True)
