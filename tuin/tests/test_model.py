"""
This procedure will test the classes of the models_graph.
"""

import datetime
import unittest
from tuin import create_app, db_model as ds
from tuin.db_model import *
from lib import my_env


# @unittest.skip("Focus on Coverage")
class TestModelGraph(unittest.TestCase):

    def setUp(self):
        # Initialize Environment
        self.app = create_app('testing')
        self.app_ctx = self.app.app_context()
        self.app_ctx.push()

    def tearDown(self):
        self.app_ctx.pop()

    """
    def test_get_node_attribs(self):
        # Get a valid node
        node_id = 150
        node = Node.query.filter_by(id=node_id).first()
        # print(node.content.body)
        for term in node.terms:
            print(term.name)

    def test_get_voc(self):
        # Get a vocabulary
        voc_id = 3
        voc = Vocabulary.query.filter_by(id=voc_id).first()
        # print("Vocabulary: " + voc.name)
        # for term in voc.terms:
            # print("Taxonomy term: " + term.name)

    def test_get_taxonomy(self):
        # Get a term
        term_id = 66
        term = Term.query.filter_by(id=term_id).first()
        print("Term: " + term.name)
        for node in term.nodes:
            print(node.content.title)

    def test_get_tax_pics(self):
        # Get a term
        term_id = 66
        node_order = Node.created.desc()
        term = Term.query.filter_by(id=term_id).one()
        print(term.nodes)
        node = Node.query.filter_by(created=1433619189).one()
        print(node)
        print(term.nodes.index(node))
        print(len(term.nodes))
        print(len(term.nodes))
        node_arr = [node for node in term.nodes if ( node.type == "flickr" or node.type == "lophoto")][48:64]
        print(len(node_arr))
        for node in term.nodes:
            print(node.content.title)
            print(node.created)
    """

    def test_archive(self):
        """
        select count(*), strftime("%Y-%m", datetime(created, 'unixepoch')) from node
        group by strftime("%Y-%m", datetime(created, 'unixepoch'))
        order by created desc

        :return:
        """
        # total_articles_query = db.func.count().label('total_articles')
        monthSel = db.func.datetime(Node.created, "unixepoch")
        monthDesc = db.func.strftime("%Y-%m", monthSel)
        # month_time = db.func.strftime('%m', Node.created).label('month')
        # query = db.session.query(year_time, month_time, total_articles_query).group_by(year_time, month_time)
        # query = db.session.query(Node, year_time).group_by(year_time).count()
        query = db.session.query(monthDesc, db.func.count()).group_by(monthDesc)
        print(query)
        # sorted_query = query.order_by(datetime.datetime.fromtimestamp(Node.created.desc()).strftim)
        # for rec in query.all():
        #     print(rec)

if __name__ == "__main__":
    unittest.main()
