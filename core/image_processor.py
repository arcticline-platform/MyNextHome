import os
from io import BytesIO

from django.db import models
from PIL import Image, ImageOps
from django.core.files import File
from django.db.models.fields.files import ImageFieldFile

# from .validators import validate_image_with_face


class CompressedImageFieldFile(ImageFieldFile):
    def save(self, name, content, save=True): 
        # Compressed Image
        image = Image.open(content)
        image = image.convert('RGB')        
        image = ImageOps.exif_transpose(image)
        im_io = BytesIO()
        image.save(im_io, "JPEG", optimize=True, quality=self.field.quality)

        # Change extension
        filename = os.path.splitext(name)[0]
        filename = f"{filename}.jpg"

        image = File(im_io, name=filename)
        super().save(filename, image, save)


class CompressedImageField(models.ImageField):
    attr_class = CompressedImageFieldFile

    def __init__(self, verbose_name=None, name=None, width_field=None, height_field=None, quality=90, **kwargs):
        self.quality = quality
        super().__init__(verbose_name, name, width_field, height_field, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.quality:
            kwargs['quality'] = self.quality
        return name, path, args, kwargs