"""The kind the viewer gives a file from its first bytes (workbench/universal_view.identify and the view modules' claims):
a picture a phone saved as HEIC or AVIF is a picture, whatever this computer can decode. 0.8.4: written for a planted bug that
stopped HEIF files being named as pictures (tools/planted_bugs, M111). Run alone:

  python -B -m unittest -v tests_integrated.test_viewer_kinds
"""
import unittest

from workbench.universal_view import Source, identify


def heif(brand):
    """The start of an ISO media file: a box size, 'ftyp', its brand, a version and the compatible brands."""
    return b'\x00\x00\x00\x1c' + b'ftyp' + brand + b'\x00\x00\x00\x00' + b'mif1' + brand + b'\x00' * 64


class PictureKinds(unittest.TestCase):
    def test_heic_and_avif_files_are_pictures(self):
        for name, brand in (('IMG_0001.heic', b'heic'), ('photo.heif', b'mif1'), ('cover.avif', b'avif')):
            self.assertEqual(identify(Source(name, data=heif(brand))), 'image', name)

    def test_a_tiff_is_a_picture_and_an_unknown_brand_is_not_one(self):
        self.assertEqual(identify(Source('scan.tif', data=b'II*\x00' + b'\x00' * 64)), 'image')
        self.assertNotEqual(identify(Source('clip.heic', data=heif(b'qt  '))), 'image')


if __name__ == '__main__':
    unittest.main()
