# import logging
import sqlite3
import time
from . import db, lm
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
# from sqlalchemy.orm.exc import NoResultFound


class Content(db.Model):
    """
    Table with Node Title and Node Contents.
    """
    __tablename__ = "content"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    node_id = db.Column(db.Integer, db.ForeignKey('node.id'))
    title = db.Column(db.Text, nullable=False)
    body = db.Column(db.Text)


class Flickr(db.Model):
    """
    Table containing details of the Flickr Picture
    """
    __tablename__ = "flickr"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    node_id = db.Column(db.Integer, db.ForeignKey('node.id'))
    photo_id = db.Column(db.Integer)
    flickrdetails = db.relationship("FlickrDetails", uselist=False)


class FlickrDetails(db.Model):
    """
    Table with the whereabouts of the Flickr pictures.
    """
    __tablename__ = "flickrdetails"
    photo_id = db.Column(db.Integer, db.ForeignKey('flickr.photo_id'), primary_key=True)
    datetaken = db.Column(db.Integer, nullable=False)
    title = db.Column(db.Text, nullable=False)
    url_c = db.Column(db.Text, nullable=False)
    url_l = db.Column(db.Text, nullable=False)
    url_m = db.Column(db.Text, nullable=False)
    url_n = db.Column(db.Text, nullable=False)
    url_o = db.Column(db.Text, nullable=False)
    url_q = db.Column(db.Text, nullable=False)
    url_s = db.Column(db.Text, nullable=False)
    url_sq = db.Column(db.Text, nullable=False)
    url_t = db.Column(db.Text, nullable=False)
    url_z = db.Column(db.Text, nullable=False)
    flickr_url = db.Column(db.Text, nullable=False)


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
    flickr = db.relationship("Flickr", backref="node", uselist=False)
    lophoto = db.relationship("Lophoto", backref="node", uselist=False)
    terms = db.relationship("Term", secondary="taxonomy", backref="nodes")

    @staticmethod
    def add(**params):
        params['created'] = int(time.time())
        params['modified'] = params['created']
        params['revcnt'] = 1
        node_inst = Node(**params)
        db.session.add(node_inst)
        db.session.commit()
        db.session.refresh(node_inst)
        return node_inst.nid

    @staticmethod
    def edit(**params):
        """
        This method will edit the node title or body.

        :param params: Dictionary with title and body as keys.

        :return:
        """
        node_inst = db.session.query(Node).filter_by(nid=params['nid']).first()
        # node_inst.title = params['title']
        # node_inst.body = params['body']
        node_inst.modified = int(time.time())
        node_inst.revcnt += 1
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
        node_inst = Node.query.filter_by(nid=nid).one()
        db.session.delete(node_inst)
        db.session.commit()
        return True


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


class Term(db.Model):
    """
    Table containing the Terms from a Vocabulary.
    """
    __tablename__ = "term"
    id = db.Column(db.Integer, primary_key=True)
    vocabulary_id = db.Column(db.Integer, db.ForeignKey("vocabulary.id"), nullable=False)
    name = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    # nodes = db.relationship("Node", secondary="taxonomy", backref="terms")


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


def get_pics(page=1):
    """
    This method will get the picture URLs for the page specified.


    :param page: Page number. Each page has 16 pictures, from most recent to oldest.

    :return:
    """
    page_size = 16
    node_order = Node.created.asc()
    nodes = Node.query.filter((Node.type == "flickr") | (Node.type == "lophoto")).order_by(node_order).limit(page_size)
    return nodes


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
    # print("{q}".format(q=str(nodes)))
    for node in nodes.all():
        params = (node.nid, "{l} {t}".format(l=level, t=node.title))

        # print("{level} {title}".format(level=level, title=node.title))
        tree.append(params)
        if node.nid != exclnid:
            tree = get_tree(parent_id=node.nid, tree=tree, level=level, exclnid=exclnid)
    return tree


def get_voc_name(id):
    """
    This method will return the vocabulary name for this ID.

    :param id: ID of the vocabulary

    :return: Name of the vocabulary (Plaats or Planten)
    """
    voc = Vocabulary.query.filter_by(id=id)
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
        # query = "CREATE VIRTUAL TABLE nodes USING fts5(nid UNINDEXED, title, body, created UNINDEXED)"
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
