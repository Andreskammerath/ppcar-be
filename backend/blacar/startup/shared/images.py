""" Module to handle images utils for our backend. """

import io
from typing import BinaryIO, Optional
from dataclasses import dataclass
from django.core.files.temp import NamedTemporaryFile as TemporaryFile
from PIL import Image as PILImage
from returns.result import Result, Success, Failure
from .exceptions import ValidationError


class ImageException(Exception):
    """ Base class for all images exceptions. """


@dataclass
class Image:
    """
    Baseclass to handle images data in our backend.
    """
    
    # Sizes
    MAX_SIZE_BYTES = 8 * (1024 * 1024)
    
    # Formats
    FORMAT_PNG  = "PNG"
    FORMAT_JPEG = "JPEG"
    FORMAT_WEBP = "WEBP"
    SUPPORTED_FORMATS = (FORMAT_PNG, FORMAT_JPEG, FORMAT_WEBP)
    
    # Properties
    width: int
    height: int
    mimetype: str
    suffix: str
    
    # Image data stream
    _data: BinaryIO
    
    def __init__(self, data: BinaryIO):
        """
        Initializes image with given data.
        
        Args:
            data (BinaryIO): Image data stream
        """
        with PILImage.open(data) as img_data:
            # Loading raw data only supported for JPEG images
            if img_data.format != self.FORMAT_JPEG:
                raise ImageException("Only JPEG images are supported when loading raw data directly")
            
            self._data = data
            self.width = img_data.width
            self.height = img_data.height
            self.mimetype = "image/jpeg"
            self.suffix = "jpg"
    
    @classmethod
    def _validate_data_size(cls, data: BinaryIO) -> Optional[ValidationError]:
        data.seek(0, io.SEEK_END)
        data_size_bytes = data.tell()
        data.seek(0)
        if data_size_bytes > cls.MAX_SIZE_BYTES:
            return ValidationError("IMAGE_TOO_BIG", detail={ 'max_size_bytes': cls.MAX_SIZE_BYTES })
    
    @classmethod
    def _validate_integrity(cls, data: BinaryIO) -> Optional[ValidationError]:
        try:
            PILImage.open(data).verify()
        except PILImage.UnidentifiedImageError:
            return ValidationError("UNIDENTIFIED_IMAGE_ERROR")
    
    @classmethod
    def _validate_format(cls, data: BinaryIO) -> Optional[ValidationError]:
        with PILImage.open(data) as img_data:
            if img_data.format not in cls.SUPPORTED_FORMATS:
                return ValidationError(
                    "INVALID_IMAGE_FORMAT",
                    detail={ 'image_format': img_data.format, 'image_allowed_formats': cls.SUPPORTED_FORMATS }
                )
    
    @classmethod
    def from_data(cls, data: BinaryIO) -> Result["Image", ValidationError]:
        
        validation_errors = ValidationError([
            cls._validate_data_size(data),
            cls._validate_integrity(data),
            cls._validate_format(data)
        ])
        
        if any(validation_errors.error_list):
            return Failure(validation_errors)
        
        # Manipulate image
        with PILImage.open(data) as img_data:
            # Loads first image then closes it to release it's memory and prevent
            # loading more than one image at a time
            final_img_data   = TemporaryFile(delete=True)
            final_img_config = {
                "format": cls.FORMAT_JPEG,
                "quality": 70,
                "optimize": True,
                "progressive": True
            }
            # Converts to JPEG as we only support it
            img_data.convert("RGB").save(final_img_data, **final_img_config)
        
        return Success(cls(data=final_img_data))

    @classmethod
    def rgb(
        cls,
        width: int,
        height: int,
        color_base: tuple[int, int, int] = (255, 255, 255)
    ) -> Success["Image"]:
        """
        Creates new RGB image with given dimensions and a color base.
        """
        
        _data = io.BytesIO()
        
        img_config = {
            "mode": "RGB", # We only support JPEG images
            "size": (width, height),
            "color": color_base
        }
        
        with PILImage.new(**img_config) as img:
            img.save(_data, format=cls.FORMAT_JPEG)
            _data.seek(0)
        
        return Success(cls(data=_data))
    
    @classmethod
    def white_pixel(cls) -> Success["Image"]:
        """ Returns little in-memory 1x1 white image. """
        return cls.rgb(width=1, height=1, color_base=(255, 255, 255))
