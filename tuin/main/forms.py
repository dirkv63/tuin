from flask_wtf import FlaskForm as Form
from wtforms import StringField, SubmitField, PasswordField, BooleanField, TextAreaField, SelectField
from wtforms import SelectMultipleField
import wtforms.validators as wtv

from wtforms.widgets import TextArea


class CKTextAreaWidget(TextArea):
    def __call__(self, field, **kwargs):
        if kwargs.get('class'):
            kwargs['class'] += ' ckeditor'
        else:
            kwargs.setdefault('class', 'ckeditor')
        return super(CKTextAreaWidget, self).__call__(field, **kwargs)


class CKTextAreaField(TextAreaField):
    widget = CKTextAreaWidget()


class Login(Form):
    username = StringField('Username', validators=[wtv.InputRequired(), wtv.Length(1, 16)])
    password = PasswordField('Password', validators=[wtv.InputRequired()])
    remember_me = BooleanField('Remember me')
    submit = SubmitField('OK')


class PwdUpdate(Form):
    current_pwd = PasswordField('Current Password', validators=[wtv.InputRequired()])
    new_pwd = PasswordField('New Password', validators=[wtv.InputRequired(),
                                                        wtv.EqualTo('confirm_pwd', message='Passwords must match'),
                                                        wtv.Length(min=4, message='Minimum length is %(min)d')])
    confirm_pwd = PasswordField('Re-Enter New Password')
    submit = SubmitField('Change')


class TextAdd(Form):
    title = StringField('Titel')
    body = CKTextAreaField('Beschrijving')
    plaats = SelectMultipleField('Plaats: ', coerce=str)
    planten = SelectMultipleField('Planten', coerce=str)
    submit = SubmitField('OK')


class NodeOutline(Form):
    parent = SelectField("Select Parent: ", coerce=str)
    submit = SubmitField('OK')


class Search(Form):
    search = StringField('Search', validators=[wtv.InputRequired()])
    submit = SubmitField('Go!')
