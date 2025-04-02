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

cd "carta_backend/proto/"

# Find all .py files that do not start with "_" and append the import statement
for file in *.py; do
    [[ "$file" == _* || "$file" == "__init__.py" ]] && continue
    module="${file%.py}"  # Remove the .py extension
    echo "from .$module import *" >> __init__.py
done

printf "...done\n"
