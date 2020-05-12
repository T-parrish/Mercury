run-dev:
	env/dev.sh

run-debug:
	env/debug.sh
    
alembic-revisions:
	alembic revision --autogenerate

migrate:
	alembic upgrade head

downgrade: 
	alembic downgrade head