# Suggest running this as 'app'
# Before running, the database server ('db') must first be started

FROM python:3.4
ENV PYTHONUNBUFFERED 1
ENV DJANGO_CONFIGURATION Docker

ENV HOME /root
RUN apt-get install postgresql-client

WORKDIR /usr/src/app
RUN git clone -b master https://github.com/GETLIMS/LIMS-Backend lims 

WORKDIR /usr/src/app/lims
RUN ls -l
RUN pip install -r requirements.txt

ENV DB_NAME postgres
ENV DB_USER postgres
ENV DB_HOST db 
ENV DB_PORT 5432
ENV SALESFORCE_USERNAME none 
ENV SALESFORCE_PASSWORD none
ENV SALESFORCE_TOKEN none
ENV PROJECT_IDENTIFIER_PREFIX GM
ENV PROJECT_IDENTIFIER_START 100 

RUN python manage.py migrate

CMD ["gunicorn", "lims.wsgi", "-w", "2", "-b", "0.0.0.0:8000", "--log-level", "-"]
