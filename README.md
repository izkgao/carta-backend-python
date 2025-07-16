# carta-backend-python

## Warning
This experimental package is still under development and not ready for production use.

## Download

```bash
git clone https://github.com/izkgao/carta-backend-python.git
cd carta-backend-python
```

## Install (using uv) (recommended)

```bash
uv sync
uv pip install -e .
source .venv/bin/activate
```

## Install (using conda/mamba/micromamba)

### Create conda environment

```bash
conda create -n carta-backend python=3.13 -y
conda activate carta-backend
```
### Install carta-backend

```bash
pip install -e .
```

## Download CARTA frontend

```bash
cd ..
mkdir carta-frontend-5.0.0
cd carta-frontend-5.0.0
wget https://registry.npmjs.org/carta-frontend/-/carta-frontend-5.0.0.tgz
tar zxvf carta-frontend-5.0.0.tgz
```

## Run CARTA

```bash
# <frontend_folder> should point to /some/path/carta-frontend-5.0.0/package/build
carta-backend --frontend_folder <frontend_folder>
```






