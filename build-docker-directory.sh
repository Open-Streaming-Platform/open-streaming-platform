# Create Docker Build Directory
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
cp installs/docker/OSP-Core/Dockerfile docker-build/osp-core
cp -R installs/docker/OSP-Core/docker-files.d docker-build/osp-core

# Build OSP-RTMP docker-build Directory
mkdir -p docker-build/osp-rtmp/installs
cp -R installs/nginx-core docker-build/osp-rtmp/installs
cp -R installs/osp-rtmp/* docker-build/osp-rtmp/
cp -R setup docker-build/osp-rtmp

cp installs/docker/OSP-RTMP/Dockerfile docker-build/osp-rtmp
cp -R installs/docker/OSP-RTMP/docker-files.d docker-build/osp-rtmp

# Build OSP-Ejabberd docker-build Directory
mkdir -p docker-build/osp-ejabberd/installs
cp -R installs/ejabberd docker-build/osp-ejabberd/installs
cp -R installs/nginx-core docker-build/osp-ejabberd/installs

cp installs/docker/Ejabberd/Dockerfile docker-build/osp-ejabberd
cp -R installs/docker/Ejabberd/docker-files.d docker-build/osp-ejabberd