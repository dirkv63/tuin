source /opt/envs/tuin/bin/activate
# launch rq worker
exec rq worker tuin-tasks &
# flask run &
exec gunicorn -b :8005 --access-logfile - --error-logfile - fromflask:app &
