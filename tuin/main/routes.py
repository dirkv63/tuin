# import logging
import tuin.db_model as ds
from flask import render_template, flash, redirect, url_for, request
from flask_login import login_required, login_user, logout_user, current_user
from .forms import *
from . import main
from tuin.db_model import *
# from lib import my_env
from config import *


@main.route('/login', methods=['GET', 'POST'])
def login():
    form = Login()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.verify_password(form.password.data):
            flash('Login not successful', "error")
            return redirect(url_for('main.login', **request.args))
        login_user(user, remember=form.remember_me.data)
        return redirect(request.args.get('next') or url_for('main.index'))
    return render_template('login.html', form=form, hdr='Login')


@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@main.route('/pwdupdate', methods=['GET', 'POST'])
@login_required
def pwd_update():
    form = PwdUpdate()
    if form.validate_on_submit():
        user = ds.load_user(current_user.get_id())
        if user is None or not user.verify_password(form.current_pwd.data):
            flash('Password update not successful', 'error')
            return redirect(url_for('main.pwd_update'))
        # User and password is OK, so update the password
        user.set_password(form.new_pwd.data)
        flash('Password changed!', 'info')
        return redirect(url_for('main.index'))
    return render_template('login.html', form=form, hdr='Change Password')


@main.route('/')
@main.route('/<page>')
@login_required
def index(page=1):
    params = dict(
        nodes=ds.get_pics().paginate(int(page), ITEMS_PER_PAGE, False),
        searchForm=Search()
    )
    return render_template("pic_matrix.html", **params)


@main.route('/archive')
@login_required
def archive():
    params = dict(
        nodes = ds.get_archive(),
        searchForm=Search()
    )
    return render_template("archive.html", **params)


@main.route('/node/<id>')
@login_required
def node(id):
    node_obj = ds.get_node_attribs(id)
    bc = ds.get_breadcrumb(id)
    params = dict(
        node=node_obj,
        breadcrumb=bc,
        searchForm=Search()
    )
    ds.History.add(id)
    return render_template('node.html', **params)


@main.route('/taxonomy/<id>')
@login_required
def taxonomy(id):
    term = Term.query.filter_by(id=id).one()
    params = dict(
        term=term,
        searchForm=Search()
    )
    return render_template("taxonomy.html", **params)



@main.route('/vocabulary/<id>')
@login_required
def vocabulary(id):
    voc = Vocabulary.query.filter_by(id=id).first()
    params = dict(
        voc=voc,
        searchForm=Search()
    )
    return render_template('vocabulary.html', **params)


@main.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    form = Search()
    if request.method == "POST":
        if form.validate_on_submit():
            term = form.search.data
            params = dict(
                title="<small>Search Results for:</small> {term}".format(term=term),
                node_list=ds.search_term(term)
            )
            return render_template('search_result.html', **params)
    return render_template('login.html', form=form, hdr='Find Term')


@main.errorhandler(404)
def not_found(e):
    return render_template("404.html", err=e)
