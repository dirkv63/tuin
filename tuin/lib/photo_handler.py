"""
This script captures all pictures ready for publishing, move each picture to original directory and creates a medium and
small version of the picture. The picture is added as a 'photo' node to the database, including indication for 'new'
picture.
"""
import os
from datetime import datetime
from flask import current_app
from pathlib import Path
from tuin.lib import pcloud_handler
from PIL import ImageFile
from PIL.ExifTags import TAGS
from PIL.Image import LANCZOS


def get_filename(file, exif):
    """
    This function calculates filename and add picture create date/time if required, to make the picture filename unique.
    If picture from Nikon (starts with DSC), _YYmmddHHMMSS is added to the filename stem. If picture from Motorola
    (starts with IMG_) then creation date/time is added already, no change in filename. If no exif information then
    picture name is returned unchanged.

    :param file: Current filename
    :param exif: Picture exif information, or None if no exif information could be extracted.
    :return: Calculated filename for Nikon pictures, unchanged filename for Motorola.
    """
    if file[:len('DSC')] != 'DSC':
        return file
    stem = file.stem
    suffix = file.suffix
    date_time_original = datetime.strptime(exif["DateTimeOriginal"], "%Y:%m:%d %H:%M:%S")
    date_time_label = date_time_original.strftime("%Y%m%d_%H%M%S")
    return "{}_{}.{}".format(stem, date_time_label, suffix)


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
        current_app.logger.warning("No EXIF info attached in {}...".format(file))
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
        logging.error("Unexpected orientation: {}".format(orientation))
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
    source_dirname = current_app.config.get("SOURCE_FOLDER")
    original_dirname = current_app.config["ORIGINAL_FOLDER"]
    medium_dirname = current_app.config["MEDIUM_FOLDER"]
    small_dirname = current_app.config["SMALL_FOLDER"]
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
    files = [file for file in files if Path(file).suffix in accepted_types]
    for file in files:
        fileid = files[file]["fileid"]
        # Get file contents and convert to an image - also required to get exif for date and time of picture taken.
        content = pcloud.get_content(files[file])
        current_app.logger.debug("File {} length: {} (expected: {})".format(file, len(content), files[file]["size"]))
        parser = ImageFile.Parser()
        parser.feed(content)
        img = parser.close()
        # Get exif information from picture
        exif = get_labeled_exif(file, img)
        # Calculate new filename including date/time picture taken
        fn = get_filename(file, exif)
        # Move file to Original directory
        pcloud.movefile(fileid, original_folderid, fn)
        # Create medium image
        medium_img = to_medium(img)
        medium_img = rotate_image(medium_img, exif["Orientation"])
        medium_ffn = os.path.join(os.getenv('LOGDIR'), file)
        medium_img.save(medium_ffn)
        res = pcloud.upload_file(file, medium_ffn, medium_folderid)
        current_app.logger.info("File {} medium format loaded, result: {}".format(file, res["result"]))
        os.remove(medium_ffn)
        # Create small image
        small_img = to_small(medium_img)
        small_ffn = os.path.join(os.getenv('LOGDIR'), file)
        small_img.save(small_ffn)
        res = pcloud.upload_file(file, small_ffn, small_folderid)
        current_app.logger.info("File {} small format loaded, result: {}".format(file, res["result"]))
        os.remove(small_ffn)
    pcloud.logout()
    current_app.logger.info("End Application")
