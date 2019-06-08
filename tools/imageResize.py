"""
This script reads from a directory and converts every image into a medium and small format. The images are saved.
"""

import logging
from tuin.lib import my_env, pcloud_handler

my_env.init_env("tuin", __file__)
pcloud = pcloud_handler.PcloudHandler()
pcloud.logout()
logging.info("End Application")
