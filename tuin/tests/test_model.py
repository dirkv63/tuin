"""
This procedure will test the classes of the models_graph.
"""

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

    def test_get_node_attribs(self):
        # Get a valid node
        node_id = 12
        node = Node.query.filter_by(id=node_id).first()
        print(node.content.body)

if __name__ == "__main__":
    unittest.main()
