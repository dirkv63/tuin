"""
This script captures all pictures ready for publishing, move each picture to original directory and creates a medium and
small version of the picture. The picture is added as a 'photo' node to the database, including indication for 'new'
picture.
"""
import os
import tuin.lib.db_model as ds
from datetime import datetime
from dateutil import tz
# from flask import current_app
from pathlib import Path
from tuin import create_app
from tuin.lib import pcloud_handler
from tuin.lib.db_model import Node, Photo, Content
from PIL import ImageFile
from PIL.ExifTags import TAGS
from PIL.Image import LANCZOS

app = create_app()
app.app_context().push()


def create_node(filename, orig, created_dt):
    """
    Function to create a node and photo record for the photo. If filename does exist already in photo table, then do not
    create Node record, only reset Photo record.

    :param filename: Calculated filename
    :param orig: Original filename
    :param created_dt: Picture (or File) creation Datetime object.
    :return:
    """
    # Check if photo already exist.
    node_id = Photo.get_node_id(filename)
    if node_id:
        app.logger.warning("Photo {} from file {} exists already, refreshed.".format(filename, orig))
        params = dict(
            node_id=node_id,
            filename=filename,
            orig_filename=orig,
            created=int(created_dt.timestamp()),
            fresh=1
        )
        Photo.edit(**params)
    else:
        # New photo, create Node record.
        app.logger.info("Photo {} from file {} created.".format(filename, orig))
        params = dict(
            type='photo',
        )
        node_id = Node.add(**params)
        params = dict(
            node_id=node_id,
            filename=filename,
            orig_filename=orig,
            created=int(created_dt.timestamp()),
            fresh=1
        )
        Photo.add(**params)
        params = dict(
            node_id=node_id,
            title="Nieuwe Foto",
            body=""
        )
        Content.update(**params)
    Node.set_created(node_id)
    return


def get_created_datetime(filedata, exif):
    """
    Function to return photo creation date/time. If exif info is available, then this is returned from exif. Otherwise
    file create time is used.

    :param filedata: File data, to be used in case exif is not available
    :param exif: Exif information (dictionary) or None  if no exif info is available.
    :return: datetime object with photo creation.
    """
    if isinstance(exif, dict):
        created_dt = datetime.strptime(exif["DateTimeOriginal"], "%Y:%m:%d %H:%M:%S")
    else:
        mytz = tz.gettz("Europe/Brussels")
        created_ts = filedata["created"]
        created_dt = datetime.strptime(created_ts, "%a, %d %b %Y %H:%M:%S %z").astimezone(mytz)
    return created_dt


def get_filename(file, created_dt):
    """
    This function calculates filename and add picture create date/time if required, to make the picture filename unique.
    If picture from Nikon (starts with DSC), _YYmmddHHMMSS is added to the filename stem. If picture from Motorola
    (starts with IMG_) then creation date/time is added already, no change in filename. If no exif information then
    picture name is returned unchanged.

    :param file: Current filename
    :param created_dt: Date/Time of Picture Creation (or File creation).
    :return: Calculated filename for Nikon pictures, unchanged filename for Motorola.
    """
    if file[:len('DSC')] != 'DSC':
        return file
    stem = Path(file).stem
    suffix = Path(file).suffix
    date_time_label = created_dt.strftime("%Y%m%d_%H%M%S")
    return "{}_{}{}".format(stem, date_time_label, suffix)


def get_labeled_exif(file, image):
    """
    This method collects the EXIF data from an image.

    :param file: Filename of the file currently processed.
    :param image: PIL Image object
    :return: Dictionary with EXIF information in readable format.
    """
    try:
        return {TAGS[k]: v for k, v in image._getexif().items() if k in TAGS}
    except AttributeError:
        app.logger.warning("No EXIF info attached in {}...".format(file))
        return None


def rotate_image(image, orientation):
    """
    This method rotates an image if required. Orientation 1 is OK, 6 is -90, 8 is +90, 3 is 180.

    :param image: Image to be rotated.
    :param orientation: current image orientation.
    :return: rotated image, or image if no rotation is required.
    """
    if orientation == 1:
        return image
    elif orientation == 6:
        angle = -90
    elif orientation == 8:
        angle = 90
    elif orientation == 3:
        angle = 180
    else:
        app.logger.error("Unexpected orientation: {}".format(orientation))
        return image
    return image.rotate(angle, expand=True)


def resize_large(size, max_length):
    """
    This method recalculates the size (width, height) tuple so that longest size equals max_length, keeping the ratio.
    If no dimension is larger than max_length, size tuple will be returned unchanged.

    :param size: tuple containing (width, height) of the image to be resized.
    :param max_length: length of longest dimension
    :return: resized tuple to max_length keeping ratio.
    """
    width, height = size
    if max_length < max([width, height]):
        # Image resize is required, calculate new size
        if height > width:
            ratio = height / max_length
            medium_width = int(width // ratio)
            size_tuple = (medium_width, max_length)
        else:
            ratio = width / max_length
            medium_height = int(height // ratio)
            size_tuple = (max_length, medium_height)
        return size_tuple
    else:
        return size


def resize_small(size, min_length):
    """
    This method recalculates the size (width, height) tuple so that the smallest size equals min_length, keeping the
    ratio. If smallest dimension is less than min_length, the tuple will be returned unchanged.

    :param size: tuple containing (width, height) of the image to be resized.
    :param min_length: length of the smallest dimension.
    :return: resized tuple (width, height) to min_length keeping ratio and ready for cropping image.
    """
    width, height = size
    if min_length < min([width, height]):
        # Image resize is required, calculate new size
        if height < width:
            ratio = height / min_length
            small_width = int(width // ratio)
            size_tuple = (small_width, min_length)
        else:
            ratio = width / min_length
            small_height = int(height // ratio)
            size_tuple = (min_length, small_height)
        return size_tuple
    else:
        return size


def to_medium(image):
    """
    This method converts the image to a medium-sized image. The longest side is 800.

    :param image: PIL Image object to be converted.
    :return:
    """
    medium_size = 800
    size_tuple = resize_large(image.size, medium_size)
    medium_image = image.resize(size_tuple, resample=LANCZOS)
    return medium_image


def to_small(image):
    """
    This method converts the medium image to a small sized cropped image. The shortest side is 150. The longest side
    will be cropped in website. Orientation is OK from creating the medium-sized image.

    :param image: PIL Image object to be converted.
    :return:
    """
    small_size = 150
    size_tuple = resize_small(image.size, small_size)
    small_image = image.resize(size_tuple, resample=LANCZOS)
    return small_image


def photo_handler():
    """
    Main function for photo handling.

    :return:
    """
    # Get directory names
    source_dirname = app.config.get("SOURCE_FOLDER")
    original_dirname = app.config["ORIGINAL_FOLDER"]
    medium_dirname = app.config["MEDIUM_FOLDER"]
    small_dirname = app.config["SMALL_FOLDER"]
    # Connect to pcloud and get directory structure
    pcloud = pcloud_handler.PcloudHandler()
    public_cloud_id = pcloud.get_public_cloud_id()
    # Get folders from Public Folder
    subdirs, _ = pcloud.folder_contents(public_cloud_id)
    # Directory names to folder IDs - remove trailing slashes from directory names
    if source_dirname:
        source_folderid = subdirs[source_dirname[:-1]]["folderid"]
    else:
        source_folderid = public_cloud_id
    original_folderid = subdirs[original_dirname[:-1]]["folderid"]
    medium_folderid = subdirs[medium_dirname[:-1]]["folderid"]
    small_folderid = subdirs[small_dirname[:-1]]["folderid"]
    # Collect files from source directory
    _, files = pcloud.folder_contents(source_folderid)
    # Only handle accepted file types
    accepted_types = [".JPG", ".jpg"]
    files = [files[file] for file in files if Path(file).suffix in accepted_types]
    for filedata in files:
        file = filedata["name"]
        fileid = filedata["fileid"]
        app.logger.debug("Working on file {}".format(file))
        # Get file contents and convert to an image - also required to get exif for date and time of picture taken.
        content = pcloud.get_content(filedata)
        app.logger.debug("File {} length: {} (expected: {})".format(file, len(content), filedata["size"]))
        parser = ImageFile.Parser()
        parser.feed(content)
        img = parser.close()
        # Get exif information from picture
        exif = get_labeled_exif(file, img)
        app.logger.debug("EXIF: {}".format(exif))
        # Calculate new filename including date/time picture taken
        created_dt = get_created_datetime(filedata, exif)
        fn = get_filename(file, created_dt)
        create_node(fn, file, created_dt)
        # Move file to Original directory
        pcloud.movefile(fileid, original_folderid, fn)
        # Create medium image
        medium_img = to_medium(img)
        if isinstance(exif, dict):
            try:
                medium_img = rotate_image(medium_img, exif["Orientation"])
            except KeyError:
                app.logger.info("{} ({}) no Orientation in exif data".format(file, fn))
        medium_ffn = os.path.join(os.getenv('LOGDIR'), fn)
        medium_img.save(medium_ffn)
        res = pcloud.upload_file(fn, medium_ffn, medium_folderid)
        app.logger.info("File {} medium format loaded, result: {}".format(fn, res["result"]))
        os.remove(medium_ffn)
        # Create small image
        small_img = to_small(medium_img)
        small_ffn = os.path.join(os.getenv('LOGDIR'), fn)
        small_img.save(small_ffn)
        res = pcloud.upload_file(fn, small_ffn, small_folderid)
        app.logger.info("File {} small format loaded, result: {}".format(fn, res["result"]))
        os.remove(small_ffn)
    pcloud.close_connection()
    nr_files = len(files)
    app.logger.info("{} pictures have been processed.".format(nr_files))
    return nr_files


def single_photo_handler(nid):
    """
    This function accepts a node ID and creates the medium and small size pictures for the photo associated with this
    node.

    :param nid: Node ID for which medium and small picture need to be created.
    :return:
    """
    # Get directory names
    original_dirname = app.config["ORIGINAL_FOLDER"]
    medium_dirname = app.config["MEDIUM_FOLDER"]
    small_dirname = app.config["SMALL_FOLDER"]
    # Connect to pcloud and get directory structure
    pcloud = pcloud_handler.PcloudHandler()
    public_cloud_id = pcloud.get_public_cloud_id()
    # Get folders from Public Folder
    subdirs, _ = pcloud.folder_contents(public_cloud_id)
    original_folderid = subdirs[original_dirname[:-1]]["folderid"]
    medium_folderid = subdirs[medium_dirname[:-1]]["folderid"]
    small_folderid = subdirs[small_dirname[:-1]]["folderid"]
    file = ds.get_file_from_nid(nid)
    _, files = pcloud.folder_contents(original_folderid)
    filedata = files[file]
    # Get file contents and convert to an image - also required to get exif for date and time of picture taken.
    content = pcloud.get_content(filedata)
    app.logger.debug("File {} length: {} (expected: {})".format(file, len(content), filedata["size"]))
    parser = ImageFile.Parser()
    parser.feed(content)
    img = parser.close()
    # Get exif information from picture
    exif = get_labeled_exif(file, img)
    # Create medium image
    medium_img = to_medium(img)
    if isinstance(exif, dict):
        try:
            medium_img = rotate_image(medium_img, exif["Orientation"])
        except KeyError:
            app.logger.info("{} no Orientation in exif data".format(file))
    medium_ffn = os.path.join(os.getenv('LOGDIR'), file)
    medium_img.save(medium_ffn)
    res = pcloud.upload_file(file, medium_ffn, medium_folderid)
    app.logger.info("File {} medium format loaded, result: {}".format(file, res["result"]))
    os.remove(medium_ffn)
    # Create small image
    small_img = to_small(medium_img)
    small_ffn = os.path.join(os.getenv('LOGDIR'), file)
    small_img.save(small_ffn)
    res = pcloud.upload_file(file, small_ffn, small_folderid)
    app.logger.info("File {} small format loaded, result: {}".format(file, res["result"]))
    os.remove(small_ffn)
    pcloud.close_connection()
    return
