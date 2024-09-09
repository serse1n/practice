FROM postgres:15

# RUN mkdir -p /var/logs/postgresql
# RUN touch /var/logs/postgresql/postgresql-15-main.log
# RUN chmod 777 /var/logs/postgresql/postgresql-15-main.log

COPY init.sql /docker-entrypoint-initdb.d/
