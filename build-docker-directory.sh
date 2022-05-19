BUILDDIR="docker-build"

# Create Docker Build Directory
mkdir -p $BUILDDIR
mkdir -p $BUILDDIR/osp-core
mkdir -p $BUILDDIR/osp-rtmp
mkdir -p $BUILDDIR/osp-proxy
mkdir -p $BUILDDIR/osp-edge
mkdir -p $BUILDDIR/osp-ejabberd

# Build OSP-Core $BUILDDIR Directory
mkdir -p $BUILDDIR/osp-core/installs

cp -R installs/nginx-core $BUILDDIR/osp-core/installs
cp -R blueprints $BUILDDIR/osp-core
cp -R classes $BUILDDIR/osp-core
cp -R conf $BUILDDIR/osp-core
cp -R functions $BUILDDIR/osp-core
cp -R globals $BUILDDIR/osp-core
cp -R logs $BUILDDIR/osp-core
cp -R setup $BUILDDIR/osp-core
cp -R static $BUILDDIR/osp-core
cp -R templates $BUILDDIR/osp-core

cp __init__.py $BUILDDIR/osp-core
cp app.py $BUILDDIR/osp-core
cp manage.py $BUILDDIR/osp-core
cp installs/docker/OSP-Core/Dockerfile $BUILDDIR/osp-core
cp -R installs/docker/OSP-Core/docker-files.d $BUILDDIR/osp-core

# Build OSP-RTMP $BUILDDIR Directory
mkdir -p $BUILDDIR/osp-rtmp/installs
cp -R installs/nginx-core $BUILDDIR/osp-rtmp/installs
cp -R installs/osp-rtmp/* $BUILDDIR/osp-rtmp/
cp -R setup $BUILDDIR/osp-rtmp

cp installs/docker/OSP-RTMP/Dockerfile $BUILDDIR/osp-rtmp
cp -R installs/docker/OSP-RTMP/docker-files.d $BUILDDIR/osp-rtmp

# Build OSP-Ejabberd $BUILDDIR Directory
mkdir -p $BUILDDIR/osp-ejabberd/installs
cp -R installs/ejabberd $BUILDDIR/osp-ejabberd/installs
cp -R installs/nginx-core $BUILDDIR/osp-ejabberd/installs

cp installs/docker/Ejabberd/Dockerfile $BUILDDIR/osp-ejabberd
cp -R installs/docker/Ejabberd/docker-files.d $BUILDDIR/osp-ejabberd