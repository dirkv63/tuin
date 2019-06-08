import tuin.db_model as ds
from flask import render_template, flash, redirect, url_for, request
from flask_login import login_required, login_user, logout_user, current_user
from .forms import *
from . import main
from tuin.db_model import *
from tuin.lib import my_env


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
@main.route('/index/<page>')
@login_required
def index(page=1):
    pics_per_page= current_app.config.get("PICS_PER_PAGE")
    public_folder = current_app.config.get("PUBLIC_FOLDER")
    params = dict(
        nodes=ds.get_pics().paginate(int(page), pics_per_page, False),
        searchForm=Search(),
        title="Overzicht",
        page=page,
        public_folder=public_folder
    )
    return render_template("pic_matrix.html", **params)


@main.route('/archive')
@main.route('/archive/<page>')
@login_required
def archive(page=1):
    items_per_page = current_app.config.get("ITEMS_PER_PAGE")
    archlist = ds.get_archive()
    start = (int(page)-1) * items_per_page
    end = int(page) * items_per_page
    max_page = ((len(archlist)-1) // items_per_page) + 1
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
    nodes_per_page = current_app.config.get("NODES_PER_PAGE")
    nodes = ds.get_nodes_for_month(ym)
    start = (int(page)-1) * nodes_per_page
    end = int(page) * nodes_per_page
    max_page = ((len(nodes)-1) // nodes_per_page) + 1
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


@main.route('/post/add', methods=['GET', 'POST'])
@main.route('/post/add/<book_id>', methods=['GET', 'POST'])
@login_required
def post_add(node_id=None, book_id=None):
    """
    This method allows to add or edit a blog text. A blog text is only text, no picture attached to it.

    :param node_id: ID of the node for edit, or None for add
    :param book_id: ID of the parent page for which the page needs to be added.
    :return:
    """
    form = TextAdd()
    form.plaats.choices = ds.get_terms("Plaats")
    form.planten.choices = ds.get_terms("Planten")
    if request.method == "GET":
        hdr = "Nieuw Bericht"
        if node_id:
            try:
                node = Node.query.filter_by(id=node_id).one()
            except NoResultFound:
                msg = "Trying to edit Node ID {nid}, but node not found".format(nid=node_id)
                current_app.logger.error(msg)
                flash(msg, "error")
            else:
                hdr = "Aanpassen {t}".format(t=node.content.title)
                form.title.data = node.content.title
                form.body.data = node.content.body
                form.plaats.data = ds.get_terms_for_node("Plaats", node_id)
                form.planten.data = ds.get_terms_for_node("Planten", node_id)
                if node.type == "flickr":
                    form.photo.data = node.flickr.photo_id
                    form.node_date.data = False
        try:
            if book_id or (node.type == "book"):
                del form.photo
        except UnboundLocalError:
            pass
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
        date_pic = form.node_date.data
        title = ds.get_title(title, planten)
        # Todo - check if test on form.photo.data is sufficient, then remove length
        if book_id:
            node_type = "book"
        elif form.photo.data:
            node_type = "flickr"
        else:
            node_type = "blog"
        params = dict(type=node_type)
        if node_type == "book":
            params["parent_id"] = book_id
        if node_id:
            params["id"] = node_id
            Node.edit(**params)
        else:
            node_id = Node.add(**params)
        params = dict(node_id=node_id, title=title, body=body)
        Content.update(**params)
        ds.update_taxonomy_for_node(node_id, plaats+planten)
        if node_type == "flickr":
            params = dict(
                node_id=node_id,
                photo_id=form.photo.data
            )
            res = Flickr.update(**params)
            if date_pic:
                Node.set_created(node_id)
        else:
            res = Flickr.delete(node_id)
        if isinstance(res, int):
            # OK, succesful
            return redirect(url_for('main.node', id=node_id))
        else:
            flash(res, "error")
            temp_attribs = dict(
                hdr="Aanpassing nodig",
                form=form,
                searchForm=Search()
            )
            return render_template('form.html', **temp_attribs)


@main.route('/post/delete/<node_id>', methods=['GET', 'POST'])
@login_required
def post_delete(node_id):
    """
    This method allows to delete a post.

    :param node_id: ID of the node for removal

    :return:
    """
    try:
        node_inst = Node.query.filter_by(id=node_id).one()
    except NoResultFound:
        msg = "Delete for Node ID {nid} not successful: Node ID not found.".format(nid=node_id)
        current_app.logger.error(msg)
        flash(msg, "error")
    else:
        title = node_inst.content.title
        Node.delete(node_id)
        msg = "Node {t} ({nid}) removed.".format(t=title, nid=node_id)
        current_app.logger.info(msg)
        flash(msg, "info")
    return redirect(url_for('main.index'))

@main.route('/post/edit/<node_id>', methods=['GET', 'POST'])
@login_required
def post_edit(node_id):
    """
    This method allows to edit a post. A post can be text only (blog) or have a link to Flickr Page ID attached.

    :param node_id: Id of the node under review

    :return:
    """
    # If node is book, then get the parent_id
    node_inst = Node.query.filter_by(id=node_id).one()
    if node_inst.type == "book":
        return post_add(node_id=node_id, book_id=node_inst.parent_id)
    else:
        return post_add(node_id=node_id)


@main.route('/taxonomy/<id>')
@main.route('/taxonomy/<id>/<page>')
@login_required
def taxonomy(id, page=1):
    items_per_page = current_app.config.get("ITEMS_PER_PAGE")
    term = Term.query.filter_by(id=id).one()
    start = (int(page)-1) * items_per_page
    end = int(page) * items_per_page
    nodes = [node for node in term.nodes]
    sel_nodes = sorted(nodes, key=lambda node: node.created, reverse=True)
    max_page = ((len(sel_nodes)-1) // items_per_page) + 1
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
    pics_per_page = current_app.config.get("PICS_PER_PAGE")
    term = Term.query.filter_by(id=id).one()
    start = (int(page)-1) * pics_per_page
    end = int(page) * pics_per_page
    nodes = [node for node in term.nodes if (node.type == "flickr" or node.type == "lophoto")]
    sel_nodes = sorted(nodes, key=lambda node: node.created, reverse=True)
    max_page = ((len(sel_nodes)-1) // pics_per_page) + 1
    params = dict(
        term_id=id,
        title=term.name,
        nodes=sel_nodes[start:end],
        page=page,
        max_page = max_page,
        searchForm=Search()
    )
    return render_template("taxpics.html", **params)


@main.route("/timeline/<term_id>/<datestamp>")
@login_required
def timeline(term_id, datestamp):
    # Get node selected
    node = Node.query.filter_by(created=datestamp).one()
    # Then find term and get node pictures related to the term and in reverse created order (youngest first)
    term = Term.query.filter_by(id=term_id).one()
    nodes = [node for node in term.nodes if (node.type == "flickr" or node.type == "lophoto")]
    sel_nodes = sorted(nodes, key=lambda node: node.created, reverse=True)
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
    if len(sel_nodes) > (pos+1):
        params["next_node"] = sel_nodes[pos+1]
    return render_template("timeline.html", **params)

@main.route("/tools/fd")
@main.route("/tools/fd/<nid>")
@login_required
def tools_fd(nid=None):
    """"
    This method will find Nodes type flickr that do not have a flickr detail attached to it.
    This is causing an application crash.
    """
    if nid:
        flash("Remove Node id {nid}".format(nid=nid), "warning")
        Node.query.filter_by(id=nid).delete()
    nodes = Node.query.filter(Node.type == "flickr", Node.flickr == None).all()
    params = dict(nodes=nodes,
                  title="Nodes with No Flickr Details",
                  nextfun="main.tools_fd",
                  searchForm=Search())
    return render_template("node_issues.html", **params)

@main.route("/tuinplan")
@login_required
def tuinplan():
    node_inst = Node.query.filter_by(id=904).one()
    body = node_inst.content.body
    return render_template("geschaaldplan.html", body=body)

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
