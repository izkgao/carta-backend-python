# carta-backend-python

## Download

```bash
git clone git@github.com:izkgao/carta-backend-python.git
cd carta-backend-python
```

## Install

### Create conda environment

```bash
conda create -n carta-backend python=3.13 -y
conda activate carta-backend
```
### Install carta-backend

```bash
pip install -e .
```

### Build protobuf

```bash
./build_proto.sh
```

## Run CARTA

```bash
carta-backend --frontend_folder <frontend_folder>
```






