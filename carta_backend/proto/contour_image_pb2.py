"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 27, 1, '', 'contour_image.proto')
_sym_db = _symbol_database.Default()
from . import defs_pb2 as defs__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x13contour_image.proto\x12\x05CARTA\x1a\ndefs.proto"\xc4\x01\n\x10ContourImageData\x12\x0f\n\x07file_id\x18\x01 \x01(\x0f\x12\x19\n\x11reference_file_id\x18\x02 \x01(\x07\x12(\n\x0cimage_bounds\x18\x03 \x01(\x0b2\x12.CARTA.ImageBounds\x12\x0f\n\x07channel\x18\x04 \x01(\x0f\x12\x0e\n\x06stokes\x18\x05 \x01(\x0f\x12\'\n\x0ccontour_sets\x18\x06 \x03(\x0b2\x11.CARTA.ContourSet\x12\x10\n\x08progress\x18\x07 \x01(\x01"\x91\x01\n\nContourSet\x12\r\n\x05level\x18\x01 \x01(\x01\x12\x19\n\x11decimation_factor\x18\x02 \x01(\x05\x12\x17\n\x0fraw_coordinates\x18\x03 \x01(\x0c\x12\x19\n\x11raw_start_indices\x18\x04 \x01(\x0c\x12%\n\x1duncompressed_coordinates_size\x18\x05 \x01(\x05b\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'contour_image_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_CONTOURIMAGEDATA']._serialized_start = 43
    _globals['_CONTOURIMAGEDATA']._serialized_end = 239
    _globals['_CONTOURSET']._serialized_start = 242
    _globals['_CONTOURSET']._serialized_end = 387