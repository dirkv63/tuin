# import logging
import tuin.db_model as ds
from flask import render_template, flash, redirect, url_for, request
from flask_login import login_required, login_user, logout_user, current_user
from .forms import *
from . import main
from tuin.db_model import *
from lib import my_env
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
        searchForm=Search(),
        title="Overzicht",
        page=page
    )
    return render_template("pic_matrix.html", **params)


@main.route('/archive')
@main.route('/archive/<page>')
@login_required
def archive(page=1):
    archlist = ds.get_archive()
    start = (int(page)-1) * ITEMS_PER_PAGE
    end = int(page) * ITEMS_PER_PAGE
    max_page = ((len(archlist)-1) // ITEMS_PER_PAGE) + 1
    params = dict(
        archlist = archlist[start:end],
        searchForm=Search(),
        page=page,
        max_page=max_page
    )
    return render_template("archive.html", **params)


@main.route('/monthlist/<ym>')
@main.route('/monthlist/<ym>/<page>')
@login_required
def monthlist(ym, page=1):
    nodes = ds.get_nodes_for_month(ym)
    start = (int(page)-1) * NODES_PER_PAGE
    end = int(page) * NODES_PER_PAGE
    max_page = ((len(nodes)-1) // NODES_PER_PAGE) + 1
    params = dict(
        ym=ym,
        title=my_env.monthdisp(ym),
        nodes=nodes[start:end],
        page=page,
        max_page=max_page,
        searchForm=Search()
    )
    return render_template("node_list.html", **params)


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
@main.route('/taxonomy/<id>/<page>')
@login_required
def taxonomy(id, page=1):
    term = Term.query.filter_by(id=id).one()
    start = (int(page)-1) * ITEMS_PER_PAGE
    end = int(page) * ITEMS_PER_PAGE
    nodes = [node for node in term.nodes]
    sel_nodes = sorted(nodes, key=lambda node: node.created, reverse=True)
    max_page = ((len(sel_nodes)-1) // ITEMS_PER_PAGE) + 1
    params = dict(
        term_id=id,
        title=term.name,
        nodes=sel_nodes[start:end],
        page=page,
        max_page=max_page,
        searchForm=Search()
    )
    return render_template("node_list.html", **params)


@main.route('/taxpics/<id>')
@main.route('/taxpics/<id>/<page>')
@login_required
def taxpics(id, page=1):
    term = Term.query.filter_by(id=id).one()
    start = (int(page)-1) * PICS_PER_PAGE
    end = int(page) * PICS_PER_PAGE
    nodes = [node for node in term.nodes if (node.type == "flickr" or node.type == "lophoto")]
    sel_nodes = sorted(nodes, key=lambda node: node.created, reverse=True)
    max_page = ((len(sel_nodes)-1) // PICS_PER_PAGE) + 1
    params = dict(
        term_id=id,
        title=term.name,
        nodes=sel_nodes[start:end],
        page=page,
        max_page = max_page,
        searchForm=Search()
    )
    return render_template("taxpics.html", **params)


@main.route('/blog/add', methods=['GET', 'POST'])
@login_required
def blog_add(node_id=None):
    """
    This method allows to add or edit a blog text. A blog text is only text, no picture attached to it.

    :param node_id: ID of the node for edit, or None for add

    :return:
    """
    form = TextAdd()
    if request.method == "GET":
        # Get Form.
        form.plaats.choices = ds.get_terms("Plaats")
        form.planten.choices = ds.get_terms("Planten")
        if node_id:
            node = Node.query.filter_by(id=node_id).one()
            hdr = "Aanpassen {t}".format(t=node.content.title)
            form.title.data = node.content.title
            form.body.data = node.content.body
            form.plaats.data = ds.get_terms_for_node("Plaats", node_id)
            form.planten.data = ds.get_terms_for_node("Planten", node_id)
        else:
            hdr = "Nieuwe Blog"
        temp_attribs = dict(
            hdr=hdr,
            form=form,
            searchForm=Search()
        )
        return render_template('form.html', **temp_attribs)
    else:
        title = form.title.data
        body = form.body.data
        plaats = form.plaats.data
        planten = form.planten.data
        params = dict(type="blog")
        if node_id:
            params["id"] = node_id
            Node.edit(**params)
        else:
            node_id = Node.add(**params)
        params = dict(node_id=node_id, title=title, body=body)
        Content.update(**params)
        ds.update_taxonomy_for_node(node_id, plaats+planten)
        return redirect(url_for('main.node', id=node_id))


@main.route('/blog/edit/<node_id>', methods=['GET', 'POST'])
@login_required
def blog_edit(node_id):
    """
    This method allows to edit a blog text. A blog text is only text, no picture attached to it.

    :param node_id: Id of the node under review

    :return:
    """
    return blog_add(node_id=node_id)


@main.route("/timeline/<term_id>/<datestamp>")
@login_required
def timeline(term_id, datestamp):
    # Get node selected
    node = Node.query.filter_by(created=datestamp).one()
    # Then find term and get node pictures related to the term and in reverse created order (youngest first)
    term = Term.query.filter_by(id=term_id).one()
    nodes = [node for node in term.nodes if (node.type == "flickr" or node.type == "lophoto")]
    sel_nodes = sorted(nodes, key=lambda node: node.created, reverse=True)
    print("Selected notes: {sn}".format(sn=sel_nodes))
    print("Node to find: {n}".format(n=node))
    # Find index of the requested node
    pos = sel_nodes.index(node)
    params = dict(
        term_id=term_id,
        title=term.name,
        node=node,
        searchForm=Search()
    )
    if pos > 0:
        params["prev_node"] = sel_nodes[pos-1]
    print("Pos: {pos} - length: {lsn}".format(pos=pos, lsn=len(sel_nodes)))
    if len(sel_nodes) > (pos+1):
        params["next_node"] = sel_nodes[pos+1]
    return render_template("timeline.html", **params)

@main.route('/vocabulary/<id>/<target>')
@login_required
def vocabulary(id, target):
    voc = Vocabulary.query.filter_by(id=id).first()
    params = dict(
        voc=voc,
        searchForm=Search(),
        target=target
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
