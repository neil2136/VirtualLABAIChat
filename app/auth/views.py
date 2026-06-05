from flask import render_template, redirect, request, url_for, flash
from flask_login import login_user, logout_user, login_required, \
    current_user
from . import auth
from .. import login_manager
from ..email import send_email
from .forms import *
from ..lib import ldap
from .usercheck import UserValid
from ..lib.mongodb import mongo
from datetime import datetime
import time
@auth.before_app_request
def before_request():
    if request.url.startswith('http://'):
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)
    if current_user.is_authenticated:
        current_user.ping()
        if not current_user.confirmed \
                and request.endpoint \
                and request.blueprint != 'auth' \
                and request.endpoint != 'static':
            return redirect(url_for('auth.unconfirmed'))

@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('main.index'))
    return render_template('auth/unconfirmed.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    db = mongo()
    form = LoginForm()
    if form.validate_on_submit():
        name = form.username.data
        pwd = form.password.data
        remember = form.remember_me.data
        print('User login attempt: '+name)
        user = db.find_one('User', 'svname', name)
        # print('view user-------%s' % user)
        if user:
            dtime = datetime.now()
            un_time = time.mktime(dtime.timetuple())
            qastatus, qamail, qasAMAccountName, qagivenName = ldap.qa_ldap_auth(name, pwd)
            if qastatus is False:
                print('check sh ldap')
                shstatus, shmail, shsAMAccountName, shgivenName = ldap.sh_ldap_auth(name, pwd)
                print('shstatus, shmail, shsAMAccountName, shgivenName: %s %s %s %s' % (shstatus, shmail, shsAMAccountName, shgivenName))
                if shstatus:
                    user_obj = UserValid(user['fullname'], user['email'], user['svname'])
                    login_user(user_obj, remember)
                    userlog = {'user': user['fullname'], 'action': 'Login',
                               'massage': ' Login successfully! Verified via AD Server .',
                               'time': dtime, 'unixtime': un_time}
                    db.insert_one('userlog', userlog)
                    desh = db.find_one('deshboard', 'id', 'totals')
                    db.update_one('deshboard', 'id', 'totals', 'visits', str(int(desh['visits'])+1))
                    return redirect(url_for('main.index'))
                flash("Login use QA and shanghai ldap failed, Please check the password", category='failed')
                render_template('auth/login.html', form=form)
            else:
                user_obj = UserValid(user['fullname'], user['email'], user['svname'])
                login_user(user_obj, remember)
                userlog = {'user': user['fullname'], 'action': 'Login',
                           'massage': ' Login successfully! Verified via QA Server .',
                           'time': dtime, 'unixtime': un_time, 'hostip': request.remote_addr}
                db.insert_one('userlog', userlog)
                desh = db.find_one('deshboard', 'id', 'totals')
                db.update_one('deshboard', 'id', 'totals', 'visits', str(int(desh['visits']) + 1))
                return redirect(url_for('main.index'))
        else:
            flash("Please input a valid username. such as: lezhang", category='failed')
            render_template('auth/login.html', form=form)

    return render_template('auth/login.html', form=form)

@login_manager.user_loader
def load_user(user_id):
    db = mongo()
    #print('user_id-----------------%s' % user_id)
    user = db.find_one('User', 'fullname', user_id)
    if not user:
        return None
    return UserValid(user['fullname'], user['email'], user['svname'])

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('main.index'))


@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data,
                    username=form.username.data,
                    password=form.password.data)
        db.session.add(user)
        db.session.commit()
        token = user.generate_confirmation_token()
        send_email(user.email, 'Confirm Your Account',
                   'auth/email/confirm', user=user, token=token)
        flash('A confirmation email has been sent to you by email.')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)


@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('main.index'))
    if current_user.confirm(token):
        db.session.commit()
        flash('You have confirmed your account. Thanks!')
    else:
        flash('The confirmation link is invalid or has expired.')
    return redirect(url_for('main.index'))


@auth.route('/confirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_email(current_user.email, 'Confirm Your Account',
               'auth/email/confirm', user=current_user, token=token)
    flash('A new confirmation email has been sent to you by email.')
    return redirect(url_for('main.index'))


@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.password.data
            db.session.add(current_user)
            db.session.commit()
            flash('Your password has been updated.')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid password.')
    return render_template("auth/change_password.html", form=form)


@auth.route('/reset', methods=['GET', 'POST'])
def password_reset_request():
    if not current_user.is_anonymous:
        return redirect(url_for('main.index'))
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.generate_reset_token()
            send_email(user.email, 'Reset Your Password',
                       'auth/email/reset_password',
                       user=user, token=token,
                       next=request.args.get('next'))
        flash('An email with instructions to reset your password has been '
              'sent to you.')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)


@auth.route('/reset/<token>', methods=['GET', 'POST'])
def password_reset(token):
    if not current_user.is_anonymous:
        return redirect(url_for('main.index'))
    form = PasswordResetForm()
    if form.validate_on_submit():
        if User.reset_password(token, form.password.data):
            db.session.commit()
            flash('Your password has been updated.')
            return redirect(url_for('auth.login'))
        else:
            return redirect(url_for('main.index'))
    return render_template('auth/reset_password.html', form=form)


@auth.route('/change_email', methods=['GET', 'POST'])
@login_required
def change_email_request():
    form = ChangeEmailForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.password.data):
            new_email = form.email.data
            token = current_user.generate_email_change_token(new_email)
            send_email(new_email, 'Confirm your email address',
                       'auth/email/change_email',
                       user=current_user, token=token)
            flash('An email with instructions to confirm your new email '
                  'address has been sent to you.')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid email or password.')
    return render_template("auth/change_email.html", form=form)


@auth.route('/change_email/<token>')
@login_required
def change_email(token):
    if current_user.change_email(token):
        db.session.commit()
        flash('Your email address has been updated.')
    else:
        flash('Invalid request.')
    return redirect(url_for('main.index'))
