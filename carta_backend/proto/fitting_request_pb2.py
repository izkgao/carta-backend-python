"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 27, 1, '', 'fitting_request.proto')
_sym_db = _symbol_database.Default()
from . import open_file_pb2 as open__file__pb2
from . import defs_pb2 as defs__pb2
from . import enums_pb2 as enums__pb2
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x15fitting_request.proto\x12\x05CARTA\x1a\x0fopen_file.proto\x1a\ndefs.proto\x1a\x0benums.proto"\x96\x02\n\x0eFittingRequest\x12\x0f\n\x07file_id\x18\x01 \x01(\x0f\x120\n\x0einitial_values\x18\x02 \x03(\x0b2\x18.CARTA.GaussianComponent\x12\x14\n\x0cfixed_params\x18\x03 \x03(\x08\x12\x11\n\tregion_id\x18\x04 \x01(\x0f\x12#\n\x08fov_info\x18\x05 \x01(\x0b2\x11.CARTA.RegionInfo\x12\x1a\n\x12create_model_image\x18\x06 \x01(\x08\x12\x1d\n\x15create_residual_image\x18\x07 \x01(\x08\x12\x0e\n\x06offset\x18\x08 \x01(\x01\x12(\n\x06solver\x18\t \x01(\x0e2\x18.CARTA.FittingSolverType"\xe3\x02\n\x0fFittingResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\t\x12/\n\rresult_values\x18\x03 \x03(\x0b2\x18.CARTA.GaussianComponent\x12/\n\rresult_errors\x18\x04 \x03(\x0b2\x18.CARTA.GaussianComponent\x12\x0b\n\x03log\x18\x05 \x01(\t\x12\'\n\x0bmodel_image\x18\x06 \x01(\x0b2\x12.CARTA.OpenFileAck\x12*\n\x0eresidual_image\x18\x07 \x01(\x0b2\x12.CARTA.OpenFileAck\x12\x14\n\x0coffset_value\x18\x08 \x01(\x01\x12\x14\n\x0coffset_error\x18\t \x01(\x01\x12\x1e\n\x16integrated_flux_values\x18\n \x03(\x01\x12\x1e\n\x16integrated_flux_errors\x18\x0b \x03(\x01"4\n\x0fFittingProgress\x12\x0f\n\x07file_id\x18\x01 \x01(\x0f\x12\x10\n\x08progress\x18\x02 \x01(\x02"\x1e\n\x0bStopFitting\x12\x0f\n\x07file_id\x18\x01 \x01(\x0fb\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'fitting_request_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_FITTINGREQUEST']._serialized_start = 75
    _globals['_FITTINGREQUEST']._serialized_end = 353
    _globals['_FITTINGRESPONSE']._serialized_start = 356
    _globals['_FITTINGRESPONSE']._serialized_end = 711
    _globals['_FITTINGPROGRESS']._serialized_start = 713
    _globals['_FITTINGPROGRESS']._serialized_end = 765
    _globals['_STOPFITTING']._serialized_start = 767
    _globals['_STOPFITTING']._serialized_end = 797