from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SelectField,\
    SubmitField, IntegerField
from wtforms.validators import DataRequired, Length, Email, Regexp
from wtforms import ValidationError
from flask_pagedown.fields import PageDownField
from ..models import Role, User


class NameForm(FlaskForm):
    name = StringField('What is your name?', validators=[DataRequired()])
    submit = SubmitField('Submit')


class EditProfileForm(FlaskForm):
    name = StringField('Real name', validators=[Length(0, 64)])
    location = StringField('Location', validators=[Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')


class EditProfileAdminForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Length(1, 64),
                                             Email()])
    username = StringField('Username', validators=[
        DataRequired(), Length(1, 64),
        Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
               'Usernames must have only letters, numbers, dots or '
               'underscores')])
    confirmed = BooleanField('Confirmed')
    role = SelectField('Role', coerce=int)
    name = StringField('Real name', validators=[Length(0, 64)])
    location = StringField('Location', validators=[Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')

    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        self.role.choices = [(role.id, role.name)
                             for role in Role.query.order_by(Role.name).all()]
        self.user = user

    def validate_email(self, field):
        if field.data != self.user.email and \
                User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_username(self, field):
        if field.data != self.user.username and \
                User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use.')


class PostForm(FlaskForm):
    body = PageDownField("What's on your mind?", validators=[DataRequired()])
    submit = SubmitField('Submit')

class CommentForm(FlaskForm):
    body = StringField('Enter your comment', validators=[DataRequired()])
    submit = SubmitField('Submit')

class WPCForm(FlaskForm):
    name = StringField('Real name', validators=[Length(0, 64)])
    wirelesspc = StringField('wirelesspc', validators=[Length(0, 64)])
    wirelesspwd = StringField('wirelesspwd', validators=[Length(0, 64)])
    wirelessstate = IntegerField(0)
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')

class CDUCtrl_list(FlaskForm):

    ccid = IntegerField(0)
    DUTID = StringField('DUTID', validators=[Length(0, 64)])
    PowerCtrler_host = StringField('PowerCtrler_host', validators=[Length(0, 64)])
    PowerChannel = StringField('PowerChannel', validators=[Length(0, 64)])
    Product = StringField('Product', validators=[Length(0, 64)])
    DUTSN = StringField('DUTSN', validators=[Length(0, 64)])
    DUTOwner = StringField('DUTOwner', validators=[Length(0, 64)])
    CDUlink = StringField('CDUlink', validators=[Length(0, 64)])
    DUTKeepAlive = StringField('DUTKeepAlive', validators=[Length(0, 64)])
    Operator = StringField('Operator', validators=[Length(0, 64)])