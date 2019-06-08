"""
This script copies a set of files from one directory to another directory.
"""

import csv
import logging
import os
from tuin.lib import my_env, pcloud_handler


from_dirname = "original"
to_dirname = "tempOrigin"

my_env.init_env("tuin", __file__)

# Get filenames for files to be converted
fd = os.getenv('LOGDIR')
fn = 'recent_img'
fln = os.path.join(fd, '{}.csv'.format(fn))

pcloud = pcloud_handler.PcloudHandler()
public_cloud_id = os.getenv("PCLOUD_PUBLIC_ID")
subdirs, files = pcloud.folder_contents(public_cloud_id)
print(subdirs)
from_dirid = subdirs[from_dirname]["folderid"]
to_dirid = subdirs[to_dirname]["folderid"]
_, from_files = pcloud.folder_contents(from_dirid)
with open(fln, 'r', newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        file = row["filename"]
        file_id = from_files[file]["fileid"]
        print("Copy file {} with ID {} to folder with ID {}".format(file, file_id, to_dirid))
        pcloud.copyfile(file_id, to_dirid)
pcloud.logout()

logging.info("End Application")
