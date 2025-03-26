"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(_runtime_version.Domain.PUBLIC, 5, 27, 1, '', 'enums.proto')
_sym_db = _symbol_database.Default()
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0benums.proto\x12\x05CARTA*\xf1\x0e\n\tEventType\x12\x0f\n\x0bEMPTY_EVENT\x10\x00\x12\x13\n\x0fREGISTER_VIEWER\x10\x01\x12\x15\n\x11FILE_LIST_REQUEST\x10\x02\x12\x15\n\x11FILE_INFO_REQUEST\x10\x03\x12\r\n\tOPEN_FILE\x10\x04\x12\x16\n\x12SET_IMAGE_CHANNELS\x10\x06\x12\x0e\n\nSET_CURSOR\x10\x07\x12\x1c\n\x18SET_SPATIAL_REQUIREMENTS\x10\x08\x12\x1e\n\x1aSET_HISTOGRAM_REQUIREMENTS\x10\t\x12\x1a\n\x16SET_STATS_REQUIREMENTS\x10\n\x12\x0e\n\nSET_REGION\x10\x0b\x12\x11\n\rREMOVE_REGION\x10\x0c\x12\x0e\n\nCLOSE_FILE\x10\r\x12\x1d\n\x19SET_SPECTRAL_REQUIREMENTS\x10\x0e\x12\x13\n\x0fSTART_ANIMATION\x10\x0f\x12\x17\n\x13START_ANIMATION_ACK\x10\x10\x12\x12\n\x0eSTOP_ANIMATION\x10\x11\x12\x17\n\x13REGISTER_VIEWER_ACK\x10\x12\x12\x16\n\x12FILE_LIST_RESPONSE\x10\x13\x12\x16\n\x12FILE_INFO_RESPONSE\x10\x14\x12\x11\n\rOPEN_FILE_ACK\x10\x15\x12\x12\n\x0eSET_REGION_ACK\x10\x16\x12\x19\n\x15REGION_HISTOGRAM_DATA\x10\x17\x12\x18\n\x14SPATIAL_PROFILE_DATA\x10\x19\x12\x19\n\x15SPECTRAL_PROFILE_DATA\x10\x1a\x12\x15\n\x11REGION_STATS_DATA\x10\x1b\x12\x0e\n\nERROR_DATA\x10\x1c\x12\x1a\n\x16ANIMATION_FLOW_CONTROL\x10\x1d\x12\x16\n\x12ADD_REQUIRED_TILES\x10\x1e\x12\x19\n\x15REMOVE_REQUIRED_TILES\x10\x1f\x12\x14\n\x10RASTER_TILE_DATA\x10 \x12\x17\n\x13REGION_LIST_REQUEST\x10!\x12\x18\n\x14REGION_LIST_RESPONSE\x10"\x12\x1c\n\x18REGION_FILE_INFO_REQUEST\x10#\x12\x1d\n\x19REGION_FILE_INFO_RESPONSE\x10$\x12\x11\n\rIMPORT_REGION\x10%\x12\x15\n\x11IMPORT_REGION_ACK\x10&\x12\x11\n\rEXPORT_REGION\x10\'\x12\x15\n\x11EXPORT_REGION_ACK\x10(\x12\x1a\n\x16SET_CONTOUR_PARAMETERS\x10-\x12\x16\n\x12CONTOUR_IMAGE_DATA\x10.\x12\x12\n\x0eRESUME_SESSION\x10/\x12\x16\n\x12RESUME_SESSION_ACK\x100\x12\x14\n\x10RASTER_TILE_SYNC\x101\x12\x18\n\x14CATALOG_LIST_REQUEST\x102\x12\x19\n\x15CATALOG_LIST_RESPONSE\x103\x12\x1d\n\x19CATALOG_FILE_INFO_REQUEST\x104\x12\x1e\n\x1aCATALOG_FILE_INFO_RESPONSE\x105\x12\x15\n\x11OPEN_CATALOG_FILE\x106\x12\x19\n\x15OPEN_CATALOG_FILE_ACK\x107\x12\x16\n\x12CLOSE_CATALOG_FILE\x108\x12\x1a\n\x16CATALOG_FILTER_REQUEST\x109\x12\x1b\n\x17CATALOG_FILTER_RESPONSE\x10:\x12\x15\n\x11SCRIPTING_REQUEST\x10;\x12\x16\n\x12SCRIPTING_RESPONSE\x10<\x12\x12\n\x0eMOMENT_REQUEST\x10=\x12\x13\n\x0fMOMENT_RESPONSE\x10>\x12\x13\n\x0fMOMENT_PROGRESS\x10?\x12\x14\n\x10STOP_MOMENT_CALC\x10@\x12\r\n\tSAVE_FILE\x10A\x12\x11\n\rSAVE_FILE_ACK\x10B\x12\x17\n\x13CONCAT_STOKES_FILES\x10E\x12\x1b\n\x17CONCAT_STOKES_FILES_ACK\x10F\x12\x16\n\x12FILE_LIST_PROGRESS\x10G\x12\x12\n\x0eSTOP_FILE_LIST\x10H\x12\x0e\n\nPV_REQUEST\x10K\x12\x0f\n\x0bPV_RESPONSE\x10L\x12\x0f\n\x0bPV_PROGRESS\x10M\x12\x10\n\x0cSTOP_PV_CALC\x10N\x12\x13\n\x0fFITTING_REQUEST\x10O\x12\x14\n\x10FITTING_RESPONSE\x10P\x12!\n\x1dSET_VECTOR_OVERLAY_PARAMETERS\x10Q\x12\x1c\n\x18VECTOR_OVERLAY_TILE_DATA\x10R\x12\x14\n\x10FITTING_PROGRESS\x10S\x12\x10\n\x0cSTOP_FITTING\x10T\x12\x13\n\x0fPV_PREVIEW_DATA\x10U\x12\x13\n\x0fSTOP_PV_PREVIEW\x10V\x12\x14\n\x10CLOSE_PV_PREVIEW\x10W\x12\x17\n\x13REMOTE_FILE_REQUEST\x10X\x12\x18\n\x14REMOTE_FILE_RESPONSE\x10Y\x12\x1c\n\x18CHANNEL_MAP_FLOW_CONTROL\x10Z*#\n\x0bSessionType\x12\x07\n\x03NEW\x10\x00\x12\x0b\n\x07RESUMED\x10\x01*X\n\x08FileType\x12\x08\n\x04CASA\x10\x00\x12\x08\n\x04CRTF\x10\x01\x12\x0b\n\x07DS9_REG\x10\x02\x12\x08\n\x04FITS\x10\x03\x12\x08\n\x04HDF5\x10\x04\x12\n\n\x06MIRIAD\x10\x05\x12\x0b\n\x07UNKNOWN\x10\x06*%\n\nRenderMode\x12\n\n\x06RASTER\x10\x00\x12\x0b\n\x07CONTOUR\x10\x01*,\n\x0fCompressionType\x12\x08\n\x04NONE\x10\x00\x12\x07\n\x03ZFP\x10\x01\x12\x06\n\x02SZ\x10\x02*\xfd\x01\n\nRegionType\x12\t\n\x05POINT\x10\x00\x12\x08\n\x04LINE\x10\x01\x12\x0c\n\x08POLYLINE\x10\x02\x12\r\n\tRECTANGLE\x10\x03\x12\x0b\n\x07ELLIPSE\x10\x04\x12\x0b\n\x07ANNULUS\x10\x05\x12\x0b\n\x07POLYGON\x10\x06\x12\x0c\n\x08ANNPOINT\x10\x07\x12\x0b\n\x07ANNLINE\x10\x08\x12\x0f\n\x0bANNPOLYLINE\x10\t\x12\x10\n\x0cANNRECTANGLE\x10\n\x12\x0e\n\nANNELLIPSE\x10\x0b\x12\x0e\n\nANNPOLYGON\x10\x0c\x12\r\n\tANNVECTOR\x10\r\x12\x0c\n\x08ANNRULER\x10\x0e\x12\x0b\n\x07ANNTEXT\x10\x0f\x12\x0e\n\nANNCOMPASS\x10\x10*D\n\rSmoothingMode\x12\x0f\n\x0bNoSmoothing\x10\x00\x12\x10\n\x0cBlockAverage\x10\x01\x12\x10\n\x0cGaussianBlur\x10\x02*\xe2\x01\n\tStatsType\x12\r\n\tNumPixels\x10\x00\x12\x0c\n\x08NanCount\x10\x01\x12\x07\n\x03Sum\x10\x02\x12\x0f\n\x0bFluxDensity\x10\x03\x12\x08\n\x04Mean\x10\x04\x12\x07\n\x03RMS\x10\x05\x12\t\n\x05Sigma\x10\x06\x12\t\n\x05SumSq\x10\x07\x12\x07\n\x03Min\x10\x08\x12\x07\n\x03Max\x10\t\x12\x0b\n\x07Extrema\x10\n\x12\x07\n\x03Blc\x10\x0b\x12\x07\n\x03Trc\x10\x0c\x12\n\n\x06MinPos\x10\r\x12\n\n\x06MaxPos\x10\x0e\x12\x08\n\x04Blcf\x10\x0f\x12\x08\n\x04Trcf\x10\x10\x12\x0b\n\x07MinPosf\x10\x11\x12\x0b\n\x07MaxPosf\x10\x12*J\n\rErrorSeverity\x12\t\n\x05DEBUG\x10\x00\x12\x08\n\x04INFO\x10\x01\x12\x0b\n\x07WARNING\x10\x02\x12\t\n\x05ERROR\x10\x03\x12\x0c\n\x08CRITICAL\x10\x04*+\n\tEntryType\x12\n\n\x06STRING\x10\x00\x12\t\n\x05FLOAT\x10\x01\x12\x07\n\x03INT\x10\x02*\x89\x01\n\x12ClientFeatureFlags\x12\x17\n\x13CLIENT_FEATURE_NONE\x10\x00\x12\n\n\x06WEB_GL\x10\x01\x12\x0c\n\x08WEB_GL_2\x10\x02\x12\x10\n\x0cWEB_ASSEMBLY\x10\x04\x12\x18\n\x14WEB_ASSEMBLY_THREADS\x10\x08\x12\x14\n\x10OFFSCREEN_CANVAS\x10\x10*\xb4\x01\n\x12ServerFeatureFlags\x12\x17\n\x13SERVER_FEATURE_NONE\x10\x00\x12\x12\n\x0eSZ_COMPRESSION\x10\x01\x12\x14\n\x10HEVC_COMPRESSION\x10\x02\x12\x15\n\x11NVENC_COMPRESSION\x10\x04\x12\r\n\tREAD_ONLY\x10\x08\x12\x14\n\x10USER_PREFERENCES\x10\x10\x12\x10\n\x0cUSER_LAYOUTS\x10 \x12\r\n\tSCRIPTING\x10@*\x9f\x01\n\x10FileFeatureFlags\x12\x15\n\x11FILE_FEATURE_NONE\x10\x00\x12\x13\n\x0fROTATED_DATASET\x10\x01\x12\x16\n\x12CHANNEL_HISTOGRAMS\x10\x02\x12\x13\n\x0fCUBE_HISTOGRAMS\x10\x04\x12\x11\n\rCHANNEL_STATS\x10\x08\x12\x0e\n\nMEAN_IMAGE\x10\x10\x12\x0f\n\x0bMIP_DATASET\x10 *&\n\x0eCoordinateType\x12\t\n\x05PIXEL\x10\x00\x12\t\n\x05WORLD\x10\x01*:\n\x0fCatalogFileType\x12\r\n\tFITSTable\x10\x00\x12\x0b\n\x07VOTable\x10\x01\x12\x0b\n\x07Unknown\x10\x02*\xa8\x01\n\nColumnType\x12\x13\n\x0fUnsupportedType\x10\x00\x12\n\n\x06String\x10\x01\x12\t\n\x05Uint8\x10\x02\x12\x08\n\x04Int8\x10\x03\x12\n\n\x06Uint16\x10\x04\x12\t\n\x05Int16\x10\x05\x12\n\n\x06Uint32\x10\x06\x12\t\n\x05Int32\x10\x07\x12\n\n\x06Uint64\x10\x08\x12\t\n\x05Int64\x10\t\x12\t\n\x05Float\x10\n\x12\n\n\x06Double\x10\x0b\x12\x08\n\x04Bool\x10\x0c*\x8d\x01\n\x12ComparisonOperator\x12\t\n\x05Equal\x10\x00\x12\x0c\n\x08NotEqual\x10\x01\x12\n\n\x06Lesser\x10\x02\x12\x0b\n\x07Greater\x10\x03\x12\x11\n\rLessorOrEqual\x10\x04\x12\x12\n\x0eGreaterOrEqual\x10\x05\x12\r\n\tRangeOpen\x10\x06\x12\x0f\n\x0bRangeClosed\x10\x07*,\n\x0bSortingType\x12\r\n\tAscending\x10\x00\x12\x0e\n\nDescending\x10\x01*\xaa\x03\n\x06Moment\x12\x18\n\x14MEAN_OF_THE_SPECTRUM\x10\x00\x12\x1e\n\x1aINTEGRATED_OF_THE_SPECTRUM\x10\x01\x12\x1c\n\x18INTENSITY_WEIGHTED_COORD\x10\x02\x12.\n*INTENSITY_WEIGHTED_DISPERSION_OF_THE_COORD\x10\x03\x12\x1a\n\x16MEDIAN_OF_THE_SPECTRUM\x10\x04\x12\x15\n\x11MEDIAN_COORDINATE\x10\x05\x12&\n"STD_ABOUT_THE_MEAN_OF_THE_SPECTRUM\x10\x06\x12\x17\n\x13RMS_OF_THE_SPECTRUM\x10\x07\x12&\n"ABS_MEAN_DEVIATION_OF_THE_SPECTRUM\x10\x08\x12\x17\n\x13MAX_OF_THE_SPECTRUM\x10\t\x12$\n COORD_OF_THE_MAX_OF_THE_SPECTRUM\x10\n\x12\x17\n\x13MIN_OF_THE_SPECTRUM\x10\x0b\x12$\n COORD_OF_THE_MIN_OF_THE_SPECTRUM\x10\x0c*&\n\nMomentAxis\x12\x0c\n\x08SPECTRAL\x10\x00\x12\n\n\x06STOKES\x10\x01*0\n\nMomentMask\x12\x08\n\x04None\x10\x00\x12\x0b\n\x07Include\x10\x01\x12\x0b\n\x07Exclude\x10\x02*\xca\x01\n\x10PolarizationType\x12\x1a\n\x16POLARIZATION_TYPE_NONE\x10\x00\x12\x05\n\x01I\x10\x01\x12\x05\n\x01Q\x10\x02\x12\x05\n\x01U\x10\x03\x12\x05\n\x01V\x10\x04\x12\x06\n\x02RR\x10\x05\x12\x06\n\x02LL\x10\x06\x12\x06\n\x02RL\x10\x07\x12\x06\n\x02LR\x10\x08\x12\x06\n\x02XX\x10\t\x12\x06\n\x02YY\x10\n\x12\x06\n\x02XY\x10\x0b\x12\x06\n\x02YX\x10\x0c\x12\n\n\x06Ptotal\x10\r\x12\x0b\n\x07Plinear\x10\x0e\x12\x0b\n\x07PFtotal\x10\x0f\x12\x0c\n\x08PFlinear\x10\x10\x12\n\n\x06Pangle\x10\x11*&\n\x0cFileListType\x12\t\n\x05Image\x10\x00\x12\x0b\n\x07Catalog\x10\x01*>\n\x12FileListFilterMode\x12\x0b\n\x07Content\x10\x00\x12\r\n\tExtension\x10\x01\x12\x0c\n\x08AllFiles\x10\x02*+\n\x0fProfileAxisType\x12\n\n\x06Offset\x10\x00\x12\x0c\n\x08Distance\x10\x01*{\n\x14PointAnnotationShape\x12\n\n\x06SQUARE\x10\x00\x12\x07\n\x03BOX\x10\x01\x12\n\n\x06CIRCLE\x10\x02\x12\x10\n\x0cCIRCLE_LINED\x10\x03\x12\x0b\n\x07DIAMOND\x10\x04\x12\x11\n\rDIAMOND_LINED\x10\x05\x12\t\n\x05CROSS\x10\x06\x12\x05\n\x01X\x10\x07*\x90\x01\n\x16TextAnnotationPosition\x12\n\n\x06CENTER\x10\x00\x12\x0e\n\nUPPER_LEFT\x10\x01\x12\x0f\n\x0bUPPER_RIGHT\x10\x02\x12\x0e\n\nLOWER_LEFT\x10\x03\x12\x0f\n\x0bLOWER_RIGHT\x10\x04\x12\x07\n\x03TOP\x10\x05\x12\n\n\x06BOTTOM\x10\x06\x12\x08\n\x04LEFT\x10\x07\x12\t\n\x05RIGHT\x10\x08*A\n\x11FittingSolverType\x12\x06\n\x02Qr\x10\x00\x12\x0c\n\x08Cholesky\x10\x01\x12\r\n\tMcholesky\x10\x02\x12\x07\n\x03Svd\x10\x03b\x06proto3')
_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'enums_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    DESCRIPTOR._loaded_options = None
    _globals['_EVENTTYPE']._serialized_start = 23
    _globals['_EVENTTYPE']._serialized_end = 1928
    _globals['_SESSIONTYPE']._serialized_start = 1930
    _globals['_SESSIONTYPE']._serialized_end = 1965
    _globals['_FILETYPE']._serialized_start = 1967
    _globals['_FILETYPE']._serialized_end = 2055
    _globals['_RENDERMODE']._serialized_start = 2057
    _globals['_RENDERMODE']._serialized_end = 2094
    _globals['_COMPRESSIONTYPE']._serialized_start = 2096
    _globals['_COMPRESSIONTYPE']._serialized_end = 2140
    _globals['_REGIONTYPE']._serialized_start = 2143
    _globals['_REGIONTYPE']._serialized_end = 2396
    _globals['_SMOOTHINGMODE']._serialized_start = 2398
    _globals['_SMOOTHINGMODE']._serialized_end = 2466
    _globals['_STATSTYPE']._serialized_start = 2469
    _globals['_STATSTYPE']._serialized_end = 2695
    _globals['_ERRORSEVERITY']._serialized_start = 2697
    _globals['_ERRORSEVERITY']._serialized_end = 2771
    _globals['_ENTRYTYPE']._serialized_start = 2773
    _globals['_ENTRYTYPE']._serialized_end = 2816
    _globals['_CLIENTFEATUREFLAGS']._serialized_start = 2819
    _globals['_CLIENTFEATUREFLAGS']._serialized_end = 2956
    _globals['_SERVERFEATUREFLAGS']._serialized_start = 2959
    _globals['_SERVERFEATUREFLAGS']._serialized_end = 3139
    _globals['_FILEFEATUREFLAGS']._serialized_start = 3142
    _globals['_FILEFEATUREFLAGS']._serialized_end = 3301
    _globals['_COORDINATETYPE']._serialized_start = 3303
    _globals['_COORDINATETYPE']._serialized_end = 3341
    _globals['_CATALOGFILETYPE']._serialized_start = 3343
    _globals['_CATALOGFILETYPE']._serialized_end = 3401
    _globals['_COLUMNTYPE']._serialized_start = 3404
    _globals['_COLUMNTYPE']._serialized_end = 3572
    _globals['_COMPARISONOPERATOR']._serialized_start = 3575
    _globals['_COMPARISONOPERATOR']._serialized_end = 3716
    _globals['_SORTINGTYPE']._serialized_start = 3718
    _globals['_SORTINGTYPE']._serialized_end = 3762
    _globals['_MOMENT']._serialized_start = 3765
    _globals['_MOMENT']._serialized_end = 4191
    _globals['_MOMENTAXIS']._serialized_start = 4193
    _globals['_MOMENTAXIS']._serialized_end = 4231
    _globals['_MOMENTMASK']._serialized_start = 4233
    _globals['_MOMENTMASK']._serialized_end = 4281
    _globals['_POLARIZATIONTYPE']._serialized_start = 4284
    _globals['_POLARIZATIONTYPE']._serialized_end = 4486
    _globals['_FILELISTTYPE']._serialized_start = 4488
    _globals['_FILELISTTYPE']._serialized_end = 4526
    _globals['_FILELISTFILTERMODE']._serialized_start = 4528
    _globals['_FILELISTFILTERMODE']._serialized_end = 4590
    _globals['_PROFILEAXISTYPE']._serialized_start = 4592
    _globals['_PROFILEAXISTYPE']._serialized_end = 4635
    _globals['_POINTANNOTATIONSHAPE']._serialized_start = 4637
    _globals['_POINTANNOTATIONSHAPE']._serialized_end = 4760
    _globals['_TEXTANNOTATIONPOSITION']._serialized_start = 4763
    _globals['_TEXTANNOTATIONPOSITION']._serialized_end = 4907
    _globals['_FITTINGSOLVERTYPE']._serialized_start = 4909
    _globals['_FITTINGSOLVERTYPE']._serialized_end = 4974