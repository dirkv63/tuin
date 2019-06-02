"""
This script handles images. It will rotate and resize images.
"""
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
    This method rotates an image if required. Orientation 1 is OK, 6 is +90, 8 is -90, 3 is 180.

    :param image: Image to be rotated.
    :param orientation: current image orientation.
    :return: rotated image
    """
    if orientation == 1:
        return image
    if orientation == 6:
        angle = -90
    elif orientation == 8:
        angle = 90
    elif orientation == 3:
        angle = 180
    return image.rotate(angle, expand=True)


def to_medium(image, width, height, orientation, ffp):
    """
    This method converts the image to a medium-sized image. The longest side is 800.

    :param image: PIL Image object to be converted.
    :param width: Width of the picture.
    :param height: Height of the picture.
    :param orientation: Current orientation of the picture.
    :param ffp: Filename (full path) of the resized image.
    :return:
    """
    medium_size = 800
    if medium_size < max([width, height]):
        # Image resize is required, calculate new size
        if height > width:
            ratio = height / medium_size
            medium_width = int(width // ratio)
            size_tuple = (medium_width, medium_size)
        else:
            ratio = width / medium_size
            medium_height = int(height // ratio)
            size_tuple = (medium_size, medium_height)
        medium_image = image.resize(size_tuple, resample=LANCZOS)
    else:
        medium_image = image
    medium_image = rotate_image(medium_image, orientation)
    medium_image.save(ffp)
    return medium_image


def to_small(image, ffp):
    """
    This method converts the medium image to a small sized cropped image. The shortest side is 150. The longest side
    will be cropped in website. Orientation is OK from creating the medium-sized image.

    :param image: PIL Image object to be converted.
    :param ffp: Filename (full path) of the resized image.
    :return:
    """
    small_size = 150
    (width, height) = image.size
    if small_size < min([width, height]):
        # Image resize is required, calculate new size
        if height < width:
            ratio = height / small_size
            small_width = int(width // ratio)
            size_tuple = (small_width, small_size)
        else:
            ratio = width / small_size
            small_height = int(height // ratio)
            size_tuple = (small_size, small_height)
        print("Resizing from {} to {}".format(image.size, size_tuple))
        small_image = image.resize(size_tuple, resample=LANCZOS)
    else:
        small_image = image
    small_image.save(ffp)
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
        medium_ffp = os.path.join(mfd, file)
        small_ffp = os.path.join(sfd, file)
        med_img = to_medium(img, exif["ExifImageWidth"], exif["ExifImageHeight"], exif["Orientation"], medium_ffp)
        to_small(med_img, small_ffp)
