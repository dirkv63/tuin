# import logging
import sqlite3
import time
from tuin import db, lm
from tuin.lib.my_env import datestamp
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound


class Content(db.Model):
    """
    Table with Node Title and Node Contents.
    """
    __tablename__ = "content"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    node_id = db.Column(db.Integer, db.ForeignKey('node.id'))
    title = db.Column(db.Text, nullable=False)
    body = db.Column(db.Text)

    @staticmethod
    def delete(nid):
        try:
            content_inst = Content.query.filter_by(node_id=nid).one()
        except NoResultFound:
            current_app.logger.info("Trying to remove content record for node id {nid}, but no record found..."
                                    .format(nid=nid))
        else:
            db.session.delete(content_inst)
            db.session.commit()
        return True

    @staticmethod
    def update(**params):
        """
        This method will add or edit the node title or body.

        :param params: Dictionary with node_id, title and body as fields.
        :return:
        """
        try:
            content_inst = db.session.query(Content).filter_by(node_id=params['node_id']).one()
            content_inst.title = params["title"]
            content_inst.body = params["body"]
        except NoResultFound:
            content_inst = Content(**params)
            db.session.add(content_inst)
        db.session.commit()
        db.session.refresh(content_inst)
        return content_inst.id


class Lophoto(db.Model):
    """
    Table containing information about the local pictures.
    """
    __tablename__ = "lophoto"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    node_id = db.Column(db.Integer, db.ForeignKey('node.id'))
    filename = db.Column(db.Text, nullable=False)
    uri = db.Column(db.Text, nullable=False)
    created = db.Column(db.Integer, nullable=False)


class Photo(db.Model):
    """
    Table containing information about the pictures on pcloud. A picture can be used by a single node only.
    """
    __tablename__ = "photo"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    node_id = db.Column(db.Integer, db.ForeignKey('node.id'))
    filename = db.Column(db.Text, nullable=False)
    orig_filename = db.Column(db.Text)
    created = db.Column(db.Integer, nullable=False)
    fresh = db.Column(db.Integer)

    @staticmethod
    def add(**params):
        photo_inst = Photo(**params)
        db.session.add(photo_inst)
        db.session.commit()
        db.session.refresh(photo_inst)
        return photo_inst.id

    @staticmethod
    def delete(node_id):
        """
        This method will delete the node - photo record. This happens when the node is deleted or if the node changes
        from type photo to type blog or when a new blog record is created, so delete may be called for non-existing
        records.
        The photo record is deleted but the photo is not removed from storage (pcloud).

        :param node_id: ID of the node attached to this picture..
        :return: 1 - integer.
        """
        try:
            photo_inst = db.session.query(Photo).filter_by(node_id=node_id).one()
        except NoResultFound:
            current_app.logger.info("Got a request to delete Photo record for node ID {nid}, but nid not found"
                                    .format(nid=node_id))
        else:
            current_app.logger.info("Delete Node {nid} with Photo ID {pid} from Photo"
                                    .format(nid=node_id, pid=photo_inst.id))
            db.session.delete(photo_inst)
            db.session.commit()
        return 1

    @staticmethod
    def edit(**params):
        """
        This method will edit the photo record, based on the Node ID. Attributes in params are set, attributes not in
        params are left untouched.

        :param params: Dictionary with node_id as identifying record.
        :return:
        """
        photo_inst = db.session.query(Photo).filter_by(node_id=params['node_id']).first()
        for k, v in params.items():
            setattr(photo_inst, k, v)
        db.session.commit()
        return

    @staticmethod
    def get_node_id(filename):
        """
        This method returns the node_id for the Photo record for picture filename, or None if the filename is not found.

        :param filename: Filename for which node_id needs to be returned.
        :return: node_id - or None if node_id is not found.
        """
        photo_inst = db.session.query(Photo).filter_by(filename=filename).first()
        if photo_inst:
            return photo_inst.node_id
        else:
            return None


class Node(db.Model):
    """
    Table containing the information of the database.
    Relationship type is called: Adjacency list.
    """
    __tablename__ = "node"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('node.id'), nullable=False)
    created = db.Column(db.Integer, nullable=False)
    modified = db.Column(db.Integer, nullable=False)
    revcnt = db.Column(db.Integer)
    type = db.Column(db.Text)
    children = db.relationship("Node",
                               backref=db.backref('parent', remote_side=[id])
                               )
    content = db.relationship("Content", backref="node", uselist=False)
    lophoto = db.relationship("Lophoto", backref="node", uselist=False)
    photo = db.relationship("Photo", backref="node", uselist=False)
    terms = db.relationship("Term", secondary="taxonomy", backref="nodes")

    @staticmethod
    def add(**params):
        params['created'] = int(time.time())
        params['modified'] = params['created']
        params['revcnt'] = 1
        if "parent_id" not in params:
            params["parent_id"] = -1
        node_inst = Node(**params)
        db.session.add(node_inst)
        db.session.commit()
        db.session.refresh(node_inst)
        return node_inst.id

    @staticmethod
    def edit(node_id):
        """
        This method will edit the node by updating modified timestamp and revision count.

        :param node_id: ID of the node to be modified.
        :return:
        """
        node_inst = db.session.query(Node).filter_by(id=node_id).first()
        node_inst.modified = int(time.time())
        node_inst.revcnt += 1
        # If node has a photo attached to it, set fresh to 0
        if node_inst.photo:
            node_inst.photo.fresh = 0
        db.session.commit()
        return

    @staticmethod
    def outline(**params):
        """
        This method will update the parent for the node. params needs to have nid and parent_id as keys.

        :param params: Dictionary with nid and parent_id as keys.
        :return:
        """
        node_inst = db.session.query(Node).filter_by(nid=params['nid']).first()
        node_inst.parent_id = params['parent_id']
        node_inst.modified = int(time.time())
        node_inst.revcnt += 1
        db.session.commit()
        return

    @staticmethod
    def delete(nid):
        try:
            node_inst = Node.query.filter_by(id=nid).one()
        except NoResultFound:
            current_app.logger.info("Trying to remove node record for node ID {nid}, but no record found"
                                    .format(nid=nid))
        else:
            if node_inst.type == "photo":
                Photo.delete(nid)
            # Remove Content record
            Content.delete(nid)
            # Then remove node record.
            db.session.delete(node_inst)
            db.session.commit()
        return True

    @staticmethod
    def set_created(nid):
        # Set node created date to Create Date picture
        node_inst = Node.query.filter_by(id=nid).one()
        nc = node_inst.created
        created = node_inst.photo.created
        current_app.logger.info("Node created datestamp from {nc} to {fd}".format(nc=datestamp(nc),
                                                                                  fd=created))
        node_inst.created = created
        db.session.commit()
        return


class History(db.Model):
    """
    Table remembering which node is selected when.
    """
    __tablename__ = "history"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    node_id = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.Integer, nullable=False)

    @staticmethod
    def add(nid):
        params = dict(
            timestamp=int(time.time()),
            node_id=nid
        )
        hist_inst = History(**params)
        db.session.add(hist_inst)
        db.session.commit()
        return


class Taxonomy(db.Model):
    """
    Table containing the taxonomy of a Node. Each term that can be assigned to the node is listed here.
    """
    __tablename__ = "taxonomy"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    node_id = db.Column(db.Integer, db.ForeignKey("node.id"), nullable=False)
    term_id = db.Column(db.Integer, db.ForeignKey("term.id"), nullable=False)
    created = db.Column(db.Integer, nullable=False)

    @staticmethod
    def add(**params):
        params['created'] = int(time.time())
        taxonomy_inst = Taxonomy(**params)
        db.session.add(taxonomy_inst)
        db.session.commit()
        db.session.refresh(taxonomy_inst)
        return taxonomy_inst.id

    @staticmethod
    def delete(**params):
        taxonomy_inst = Taxonomy.query.filter_by(node_id=params["node_id"], term_id=params["term_id"]).one()
        db.session.delete(taxonomy_inst)
        db.session.commit()
        return True


class Term(db.Model):
    """
    Table containing the Terms from a Vocabulary.
    """
    __tablename__ = "term"
    id = db.Column(db.Integer, primary_key=True)
    vocabulary_id = db.Column(db.Integer, db.ForeignKey("vocabulary.id"), nullable=False)
    name = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)

    @staticmethod
    def add(**params):
        term_inst = Term(**params)
        db.session.add(term_inst)
        db.session.commit()
        db.session.refresh(term_inst)
        return term_inst.nid


class Vocabulary(db.Model):
    """
    Table containing the Taxonomy Vocabularies. In Drupal, vocabularies were 'Plaats' and 'Planten'.
    """
    __tablename__ = "vocabulary"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text, nullable=False, unique=True)
    description = db.Column(db.Text)
    weight = db.Column(db.Integer)
    terms = db.relationship("Term", backref="vocabularies", order_by="Term.name")


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(10), index=True, unique=True)
    password_hash = db.Column(db.String(256))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def register(username, password):
        user = User()
        user.username = username
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

    @staticmethod
    def update_password(user, password):
        user.password_hash = generate_password_hash(password)
        db.session.commit(user)
        return

    def __repr__(self):
        return "<User: {user}>".format(user=self.username)


def init_session(dbconn, echo=False):
    """
    This function configures the connection to the database and returns the session object.

    :param dbconn: Name of the sqlite3 database.
    :param echo: True / False, depending if echo is required. Default: False
    :return: session object.
    """
    conn_string = "sqlite:///{db}".format(db=dbconn)
    engine = set_engine(conn_string, echo)
    session = set_session4engine(engine)
    return session


def set_engine(conn_string, echo=False):
    engine = create_engine(conn_string, echo=echo)
    return engine


def set_session4engine(engine):
    session_class = sessionmaker(bind=engine)
    session = session_class()
    return session


@lm.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def count_nf():
    """
    Function to return the count of the "Nieuwe Foto's".

    :return:
    """
    return Photo.query.filter_by(fresh=1).count()


def get_archive():
    """
    This function will collect the articles by month. SQL query:
    select count(*), strftime("%Y-%m", datetime(created, 'unixepoch')) from node
    group by strftime("%Y-%m", datetime(created, 'unixepoch'))
    order by created desc

    :return: Year - month (%Y-%m) and number of nodes created in this month, sorted from youngest to oldest.
    """
    month_sel = db.func.datetime(Node.created, "unixepoch")
    month_desc = db.func.strftime("%Y-%m", month_sel).label("monthDesc")
    query = db.session.query(month_desc, db.func.count().label("cnt"))\
        .group_by(month_desc).order_by(Node.created.desc())
    return query.all()


def get_breadcrumb(nid, bc=None):
    """
    This function will get the breadcrumb for the node. It will find the parent's node until root
    (there is no more node).
    For adding a new node, add nid for the new parent and add bc=[current_node].

    :param nid:

    :param bc: Breadcrumb list so far

    :return: bc
    """
    if not bc:
        bc = []
    node = get_node_attribs(nid=nid)
    if node.parent_id == -1:
        # Found the root node
        return bc
    else:
        parent = get_node_attribs(nid=node.parent_id)
        # bc.append(parent)
        bc[:0] = [parent]
        return get_breadcrumb(parent.id, bc)


def get_file_from_nid(nid):
    """
    This method returns the filename associated with the node ID.

    :param nid: Node ID for which the filename is required.
    :return: Filename associated with Node ID.
    """
    node_inst = Node.query.filter_by(id=nid).first()
    if node_inst:
        return node_inst.photo.filename
    else:
        current_app.logger.warning("Filename for node id {} requested but not found".format(nid))
        return None


def get_node_attribs(nid):
    """
    This method will collect the attributes required to display a node.

    :param nid: Node ID for the node
    :return: Dictionary with the attributes required to display the node.
    """
    node = Node.query.filter_by(id=nid).one()
    return node


def get_node_list(order="created"):
    """
    This method will return the most recent posts.

    :param order: This specifies the order for the list. Options: created (default), modified

    :return: Query object with nodes according to sort sequence.
    """
    node_order = Node.created.desc()
    if order == "modified":
        node_order = Node.modified.desc()
    node_list = Node.query.order_by(node_order)
    return node_list


def get_nodes_for_month(ym):
    """
    This method will return the list of nodes that were created in a specific month.

    :param ym: Month is format YYYY-MM

    :return: Nodes that have been created in this month.
    """
    month_sel = db.func.datetime(Node.created, "unixepoch")
    month_desc = db.func.strftime("%Y-%m", month_sel).label("monthDesc")
    query = db.session.query(Node).filter(month_desc == ym).order_by(Node.created.desc())
    return query.all()


def get_oldest_nf():
    """
    Function to return the oldest 'Nieuwe Foto' for processing.

    :return:
    """
    photo_inst = Photo.query.filter_by(fresh=1).order_by(Photo.created.asc()).first()
    if photo_inst:
        return photo_inst.node_id
    else:
        current_app.logger.warning("Get Oldest called, but no 'Nieuwe Foto' found.")
        return None


def get_pics():
    """
    This method will get the picture URLs for the page specified.

    :return:
    """
    node_order = Node.created.desc()
    nodes = Node.query.filter((Node.type == "photo") | (Node.type == "lophoto")).order_by(node_order)
    return nodes


def get_pics_tax(tax=1):
    """
    This method will get the picture URLs for the page and taxonomy term specified.

    :param tax: Taxonomy term ID

    :return:
    """
    node_order = Node.created.desc()
    nodes = Node.query.filter((Node.terms.id == tax)).order_by(node_order)
    return nodes


def get_terms(voc):
    """
    This method will return the terms for a vocabulary in (value, label) pairs. This can be used in SelectMultipleField
    item.

    :param voc: Vocabulary name

    :return: Terms of the vocabulary in (value, label) pair.
    """
    voc = Vocabulary.query.filter_by(name=voc).one()
    terms = [(term.id, term.name) for term in voc.terms]
    return terms


def get_terms_for_node(voc, node_id):
    """
    This method will return the selected terms for a vocabulary for a specific node.

    :param voc: Vocabulary name

    :param node_id: ID of the node.

    :return: List of term IDs
    """
    voc = Vocabulary.query.filter_by(name=voc).one()
    term_ids = [term.id for term in voc.terms]
    taxonomies = Taxonomy.query.filter(Taxonomy.term_id.in_(term_ids), Taxonomy.node_id == node_id)
    terms = [str(tax.term_id) for tax in taxonomies]
    return terms


def get_title(title, planten):
    """
    This method will return the title for a node. If the title field is not empty, then this is returned. Otherwise if
    at least 1 plant is selected from the vocabulary, the list of selected planten is chosen as title. Otherwise (No
    title) is returned as title.

    :param title: Current setting for the title
    :param planten: List of planten selected for the post.
    :return: title, list of planten or (Geen Titel).
    """
    if title:
        if not title == "Nieuwe Foto":
            return title
    if len(planten) > 0:
        # Convert term.id to term.name
        query = Term.query.filter(Term.id.in_(planten))
        current_app.logger.warning(query)
        plant_arr = [term.name for term in query.all()]
        return ", ".join(plant_arr)
    else:
        return "(Geen titel)"


def get_tree(parent_id=-1, tree=None, level="", exclnid=-1):
    """
    This method will get the full node tree sorted on title and depth first in a recursive way

    :param parent_id: ID for the parent
    :param tree: Node tree so far
    :param level: Level so far.
    :param exclnid: Specifies node nid for which descendants do not need to be acquired. For adding a node to
    another parent, then the node itself and its children should not be included, so exclnid needs to be nid
    of the node that will be moved.
    :return: list with (nid, label) per node. This is format required by SelectField.
    """
    if not tree:
        tree = []
    # nodes = Node.query.filter_by(parent_id=parent_id).order_by("title")
    nodes = Node.query.filter(Node.parent_id == parent_id, Node.nid != exclnid).order_by("title")
    level += "-"
    for node in nodes.all():
        params = (node.nid, "{lvl} {t}".format(lvl=level, t=node.title))

        tree.append(params)
        if node.nid != exclnid:
            tree = get_tree(parent_id=node.nid, tree=tree, level=level, exclnid=exclnid)
    return tree


def get_voc_name(nid):
    """
    This method will return the vocabulary name for this ID.

    :param nid: ID of the vocabulary

    :return: Name of the vocabulary (Plaats or Planten)
    """
    voc = Vocabulary.query.filter_by(id=nid)
    return voc


def search_term(term):
    """
    Trying to work from https://www.sqlite.org/fts5.html
    :param term:
    :return:
    """
    sc = sqlite3.connect(':memory:')
    with sc:
        sc.row_factory = sqlite3.Row
        sc_cur = sc.cursor()
        query = "CREATE VIRTUAL TABLE nodes USING fts4(nid, title, body, created, parent," \
                "notindexed=nid, notindexed=created, notindexed=parent)"
        sc.execute(query)
        nodes = Node.query.all()
        for node in nodes:
            if node.parent_id > 0:
                parent = get_node_attribs(node.parent_id)
                category = parent.content.title
            else:
                category = "Main"
            query = "INSERT INTO nodes (nid, title, body, created, parent) VALUES (?, ?, ?, ?, ?)"
            sc_cur.execute(query, (node.id, node.content.title, node.content.body, node.created, category))
        # logging.info("Table populated")
        # query = "SELECT * FROM nodes WHERE nodes MATCH ? ORDER BY bm25(nodes)"
        query = "SELECT distinct * FROM nodes WHERE nodes MATCH ?"
        res = sc_cur.execute(query, (term, ))
        return res


def update_taxonomy_for_node(nid, req_terms=None):
    """
    This method will update taxonomy terms for a node. It will get the list of taxonomy terms, add the new ones and
    remove the taxonomy terms that used to exist, but do not exist anymore.
    The method works for all vocabulary terms in the same process. The method also works for add, update or delete. For
    delete the terms array needs to be empty.

    :param nid: Node Id

    :param req_terms: List of taxonomy term IDs that apply to the node Id

    :return:
    """
    if req_terms:
        terms = [int(term) for term in req_terms]
    else:
        terms = []
    # Get list of current taxonomy terms for the node
    params = dict(node_id=nid)
    tax_list = Taxonomy.query.filter_by(node_id=nid)
    current_terms = [tax.term_id for tax in tax_list]
    # Add new taxonomy terms
    for term in terms:
        if term not in current_terms:
            params["term_id"] = term
            Taxonomy.add(**params)
    # Remove old taxonomy terms
    for term in current_terms:
        if term not in terms:
            params["term_id"] = term
            Taxonomy.delete(**params)
    return
