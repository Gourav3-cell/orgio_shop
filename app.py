import os
from datetime import datetime
from flask import Flask, render_template, url_for, flash, redirect, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, current_user, logout_user, login_required
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Optional
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ------------------------------
# App Initialization
# ------------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'  # Change this!
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'admin_login'
login_manager.login_message = 'Please log in to access the admin area.'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ------------------------------
# Database Models
# ------------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class PortfolioItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50))
    image_file = db.Column(db.String(100), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    is_featured = db.Column(db.Boolean, default=False)

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    message = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer)
    date_submitted = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

# Create tables and default admin
with app.app_context():
    db.create_all()
    if not User.query.first():
        admin = User(username='admin')
        admin.set_password('admin123')  # CHANGE AFTER FIRST LOGIN
        db.session.add(admin)
        db.session.commit()

# ------------------------------
# Login Manager
# ------------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ------------------------------
# Forms
# ------------------------------
class PortfolioForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    category = SelectField('Category', choices=[
        ('Video Editing', 'Video Editing'),
        ('Cards', 'Event & Digital Cards'),
        ('Posters', 'Posters & Visiting Cards'),
        ('Marketing', 'Digital Marketing')
    ])
    image = FileField('Image', validators=[FileAllowed(ALLOWED_EXTENSIONS, 'Images only!')])
    is_featured = BooleanField('Show on homepage')

class FeedbackForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[Optional()])  # No email validator needed
    message = TextAreaField('Message', validators=[DataRequired()])
    rating = IntegerField('Rating (1-5)', validators=[Optional()])

# ------------------------------
# Helper: Save uploaded file
# ------------------------------
def save_file(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{datetime.utcnow().timestamp()}{ext}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return filename
    return None

# ------------------------------
# Public Routes
# ------------------------------
@app.route('/')
def index():
    featured = PortfolioItem.query.filter_by(is_featured=True).order_by(PortfolioItem.date_created.desc()).limit(3).all()
    return render_template('index.html', featured=featured)

@app.route('/portfolio')
def portfolio():
    items = PortfolioItem.query.order_by(PortfolioItem.date_created.desc()).all()
    return render_template('portfolio.html', items=items)

@app.route('/portfolio/<int:id>')
def portfolio_item(id):
    item = PortfolioItem.query.get_or_404(id)
    return render_template('portfolio_item.html', item=item)

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    form = FeedbackForm()
    if form.validate_on_submit():
        fb = Feedback(
            name=form.name.data,
            email=form.email.data,
            message=form.message.data,
            rating=form.rating.data
        )
        db.session.add(fb)
        db.session.commit()
        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('index'))
    return render_template('feedback.html', form=form)

# ------------------------------
# Admin Routes
# ------------------------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('admin/login.html')

@app.route('/admin/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    return render_template('admin/dashboard.html')

# Portfolio management
@app.route('/admin/portfolio')
@login_required
def admin_portfolio():
    items = PortfolioItem.query.order_by(PortfolioItem.date_created.desc()).all()
    return render_template('admin/manage_portfolio.html', items=items)

@app.route('/admin/portfolio/new', methods=['GET', 'POST'])
@login_required
def new_portfolio():
    form = PortfolioForm()
    if form.validate_on_submit():
        file = request.files.get('image')
        if file and allowed_file(file.filename):
            filename = save_file(file)
        else:
            filename = 'default.jpg'
            flash('No image uploaded or invalid file. Using default.', 'warning')

        item = PortfolioItem(
            title=form.title.data,
            description=form.description.data,
            category=form.category.data,
            image_file=filename,
            is_featured=form.is_featured.data
        )
        db.session.add(item)
        db.session.commit()
        flash('Portfolio item added!', 'success')
        return redirect(url_for('admin_portfolio'))
    return render_template('admin/edit_portfolio.html', form=form, item=None)

@app.route('/admin/portfolio/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_portfolio(id):
    item = PortfolioItem.query.get_or_404(id)
    form = PortfolioForm(obj=item)
    if form.validate_on_submit():
        item.title = form.title.data
        item.description = form.description.data
        item.category = form.category.data
        item.is_featured = form.is_featured.data

        file = request.files.get('image')
        if file and allowed_file(file.filename):
            if item.image_file != 'default.jpg':
                old_file = os.path.join(app.config['UPLOAD_FOLDER'], item.image_file)
                if os.path.exists(old_file):
                    os.remove(old_file)
            filename = save_file(file)
            item.image_file = filename
        db.session.commit()
        flash('Portfolio item updated!', 'success')
        return redirect(url_for('admin_portfolio'))
    return render_template('admin/edit_portfolio.html', form=form, item=item)

@app.route('/admin/portfolio/delete/<int:id>', methods=['POST'])
@login_required
def delete_portfolio(id):
    item = PortfolioItem.query.get_or_404(id)
    if item.image_file != 'default.jpg':
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], item.image_file)
        if os.path.exists(file_path):
            os.remove(file_path)
    db.session.delete(item)
    db.session.commit()
    flash('Portfolio item deleted!', 'success')
    return redirect(url_for('admin_portfolio'))

# Feedback management
@app.route('/admin/feedback')
@login_required
def admin_feedback():
    feedbacks = Feedback.query.order_by(Feedback.date_submitted.desc()).all()
    return render_template('admin/feedback_list.html', feedbacks=feedbacks)

@app.route('/admin/feedback/delete/<int:id>', methods=['POST'])
@login_required
def delete_feedback(id):
    fb = Feedback.query.get_or_404(id)
    db.session.delete(fb)
    db.session.commit()
    flash('Feedback deleted!', 'success')
    return redirect(url_for('admin_feedback'))

# ------------------------------
# Error Handlers
# ------------------------------
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# ------------------------------
# Run
# ------------------------------
if __name__ == '__main__':
    app.run(debug=True)