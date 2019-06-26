"""
This procedure will test the functionality of the pcloud library.
"""

import unittest

from tuin import create_app
from tuin.lib import pcloud_handler, photo_handler


# @unittest.skip("Focus on Coverage")
class TestPcloud(unittest.TestCase):

    def setUp(self):
        # Initialize Environment
        self.app = create_app()
        self.app_ctx = self.app.app_context()
        self.app_ctx.push()
        self.pcloud = pcloud_handler.PcloudHandler()

    def tearDown(self):
        self.pcloud.close_connection()
        self.app_ctx.pop()

    def test_get_public_folder_id(self):
        pid = self.pcloud.get_public_cloud_id()
        self.assertTrue(isinstance(pid, int))
        self.assertEqual(len(str(pid)), 10)

    def test_photo_handler(self):
        photo_handler.photo_handler()


if __name__ == "__main__":
    unittest.main()
