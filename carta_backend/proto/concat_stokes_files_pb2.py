"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 27, 1, '', 'concat_stokes_files.proto')
_sym_db = _symbol_database.Default()
from . import enums_pb2 as enums__pb2
from . import open_file_pb2 as open__file__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x19concat_stokes_files.proto\x12\x05CARTA\x1a\x0benums.proto\x1a\x0fopen_file.proto"u\n\x11ConcatStokesFiles\x12\'\n\x0cstokes_files\x18\x01 \x03(\x0b2\x11.CARTA.StokesFile\x12\x0f\n\x07file_id\x18\x02 \x01(\x0f\x12&\n\x0brender_mode\x18\x03 \x01(\x0e2\x11.CARTA.RenderMode"n\n\nStokesFile\x12\x11\n\tdirectory\x18\x01 \x01(\t\x12\x0c\n\x04file\x18\x02 \x01(\t\x12\x0b\n\x03hdu\x18\x03 \x01(\t\x122\n\x11polarization_type\x18\x04 \x01(\x0e2\x17.CARTA.PolarizationType"c\n\x14ConcatStokesFilesAck\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\t\x12)\n\ropen_file_ack\x18\x03 \x01(\x0b2\x12.CARTA.OpenFileAckb\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'concat_stokes_files_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_CONCATSTOKESFILES']._serialized_start = 66
    _globals['_CONCATSTOKESFILES']._serialized_end = 183
    _globals['_STOKESFILE']._serialized_start = 185
    _globals['_STOKESFILE']._serialized_end = 295
    _globals['_CONCATSTOKESFILESACK']._serialized_start = 297
    _globals['_CONCATSTOKESFILESACK']._serialized_end = 396