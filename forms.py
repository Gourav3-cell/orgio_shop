from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Email, Optional

class PortfolioForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    category = SelectField('Category', choices=[('Video Editing', 'Video Editing'),
                                                ('Cards', 'Event & Digital Cards'),
                                                ('Posters', 'Posters & Visiting Cards'),
                                                ('Marketing', 'Digital Marketing')])
    image = FileField('Image', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    is_featured = BooleanField('Show on homepage')

class FeedbackForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[Optional(), Email()])
    message = TextAreaField('Message', validators=[DataRequired()])
    rating = IntegerField('Rating (1-5)', validators=[Optional()])