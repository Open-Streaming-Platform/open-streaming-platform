mkdir -p docker-build
mkdir -p docker-build/osp-core
mkdir -p docker-build/osp-rtmp
mkdir -p docker-build/osp-proxy
mkdir -p docker-build/osp-edge
mkdir -p docker-build/osp-ejabberd

# Build OSP-Core docker-build Directory
mkdir -p docker-build/osp-core/installs

cp -R installs/nginx-core docker-build/osp-core/installs
cp -R blueprints docker-build/osp-core
cp -R classes docker-build/osp-core
cp -R conf docker-build/osp-core
cp -R functions docker-build/osp-core
cp -R globals docker-build/osp-core
cp -R logs docker-build/osp-core
cp -R setup docker-build/osp-core
cp -R static docker-build/osp-core
cp -R templates docker-build/osp-core

cp __init__.py docker-build/osp-core
cp app.py docker-build/osp-core
cp manage.py docker-build/osp-core

# Build OSP-RTMP docker-build Directory
mkdir -p docker-build/osp-rtmp/installs
cp -R installs/nginx-core docker-build/osp-rtmp/installs
cp -R installs/osp-rtmp docker-build/osp-rtmp/installs
cp -R setup docker-build/osp-rtmp

# Build OSP-Ejabberd docker-build Directory
mkdir -p docker-build/osp-ejabberd/installs
cp -R installs/ejabberd docker-build/osp-ejabberd/installs
cp -R installs/nginx-core docker-build/osp-ejabberd/installs