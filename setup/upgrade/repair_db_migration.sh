sudo mysql --database="osp" --execute="DROP TABLE alembic_version"
cd /opt/osp
python3 manage.py db stamp head
