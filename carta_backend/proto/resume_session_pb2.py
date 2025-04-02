"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 29, 3, '', 'resume_session.proto')
_sym_db = _symbol_database.Default()
from . import defs_pb2 as defs__pb2
from . import enums_pb2 as enums__pb2
from . import open_catalog_file_pb2 as open__catalog__file__pb2
from . import contour_pb2 as contour__pb2
from . import concat_stokes_files_pb2 as concat__stokes__files__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x14resume_session.proto\x12\x05CARTA\x1a\ndefs.proto\x1a\x0benums.proto\x1a\x17open_catalog_file.proto\x1a\rcontour.proto\x1a\x19concat_stokes_files.proto"\x9f\x03\n\x0fImageProperties\x12\x11\n\tdirectory\x18\x01 \x01(\t\x12\x0c\n\x04file\x18\x02 \x01(\t\x12\x10\n\x08lel_expr\x18\x03 \x01(\x08\x12\x0b\n\x03hdu\x18\x04 \x01(\t\x12\x0f\n\x07file_id\x18\x05 \x01(\x0f\x12&\n\x0brender_mode\x18\x06 \x01(\x0e2\x11.CARTA.RenderMode\x12\x0f\n\x07channel\x18\x07 \x01(\x0f\x12\x0e\n\x06stokes\x18\x08 \x01(\x0f\x124\n\x07regions\x18\t \x03(\x0b2#.CARTA.ImageProperties.RegionsEntry\x125\n\x10contour_settings\x18\n \x01(\x0b2\x1b.CARTA.SetContourParameters\x12\'\n\x0cstokes_files\x18\x0b \x03(\x0b2\x11.CARTA.StokesFile\x12\x19\n\x11support_aips_beam\x18\x0c \x01(\x08\x1aA\n\x0cRegionsEntry\x12\x0b\n\x03key\x18\x01 \x01(\x0f\x12 \n\x05value\x18\x02 \x01(\x0b2\x11.CARTA.RegionInfo:\x028\x01"f\n\rResumeSession\x12&\n\x06images\x18\x01 \x03(\x0b2\x16.CARTA.ImageProperties\x12-\n\rcatalog_files\x18\x02 \x03(\x0b2\x16.CARTA.OpenCatalogFile"4\n\x10ResumeSessionAck\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\tb\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'resume_session_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_IMAGEPROPERTIES_REGIONSENTRY']._loaded_options = None
    _globals['_IMAGEPROPERTIES_REGIONSENTRY']._serialized_options = b'8\x01'
    _globals['_IMAGEPROPERTIES']._serialized_start = 124
    _globals['_IMAGEPROPERTIES']._serialized_end = 539
    _globals['_IMAGEPROPERTIES_REGIONSENTRY']._serialized_start = 474
    _globals['_IMAGEPROPERTIES_REGIONSENTRY']._serialized_end = 539
    _globals['_RESUMESESSION']._serialized_start = 541
    _globals['_RESUMESESSION']._serialized_end = 643
    _globals['_RESUMESESSIONACK']._serialized_start = 645
    _globals['_RESUMESESSIONACK']._serialized_end = 697