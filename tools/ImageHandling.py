"""
This script handles images. It will rotate and resize images.
"""
import logging
import os
from PIL import Image
from PIL.ExifTags import TAGS
from PIL.Image import LANCZOS


def get_labeled_exif(image):
    """
    This method collects the EXIF data from an image.

    :param image: PIL Image object
    :return: Dictionary with EXIF information in readable format.
    """
    try:
        return {TAGS[k]: v for k, v in image._getexif().items() if k in TAGS}
    except AttributeError:
        print("No EXIF info attached...")
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


fd = '/home/dirk/temp/pic'
mfd = '/home/dirk/temp/pic2'
sfd = '/home/dirk/temp/pic3'
for _, _, files in os.walk(fd):
    for file in sorted(files):
        print("Working on {}".format(file))
        fn = os.path.join(fd, file)
        img = Image.open(fn)
        exif = get_labeled_exif(img)
        small_ffp = os.path.join(sfd, file)
        # Resize image
        med_img = to_medium(img)
        # Rotate image
        med_img = rotate_image(med_img, exif["Orientation"])
        # Save image
        med_img.save(os.path.join(mfd, file))
        # Convert middle to small
        small_img = to_small(med_img)
        small_img.save(os.path.join(sfd, file))
