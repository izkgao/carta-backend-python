cd "$(dirname "$0")"
mkdir -p carta_backend/proto/

printf "Building all modules..."

protoc --python_out=carta_backend/proto/ \
--proto_path=carta-protobuf/shared/ \
--proto_path=carta-protobuf/control/ \
--proto_path=carta-protobuf/request/ \
--proto_path=carta-protobuf/stream/ \
carta-protobuf/*/*.proto

protol --create-package --in-place \
--python-out=carta_backend/proto/ \
protoc \
--proto-path=carta-protobuf/shared/ \
--proto-path=carta-protobuf/control/ \
--proto-path=carta-protobuf/request/ \
--proto-path=carta-protobuf/stream/ \
carta-protobuf/*/*.proto

printf "...done\n"
