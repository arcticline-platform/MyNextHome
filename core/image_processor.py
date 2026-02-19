import os
from io import BytesIO

from django.db import models
from PIL import Image, ImageOps
from django.core.files import File
from django.db.models.fields.files import ImageFieldFile

# from .validators import validate_image_with_face


class CompressedImageFieldFile(ImageFieldFile):
    def save(self, name, content, save=True): 
        try:
            # Compressed Image
            image = Image.open(content)
            
            # Change extension to .jpg for the final saved file
            filename = os.path.splitext(name)[0]
            filename = f"{filename}.jpg"
            
            # Handle transparency (RGBA/P) by pasting onto a white background
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1]) # Use alpha channel as mask
                image = background
            else:
                image = image.convert('RGB')
                
            image = ImageOps.exif_transpose(image)
            im_io = BytesIO()
            image.save(im_io, "JPEG", optimize=True, quality=self.field.quality)

            image_file = File(im_io, name=filename)
            super().save(filename, image_file, save)
        except Exception:
            # Fallback to normal save if PIL fails (though validation should catch this)
            super().save(name, content, save)


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