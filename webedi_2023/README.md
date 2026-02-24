# WebEDI
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## Overview
This repo contains code for the WebEDI web service and workers.

- The web service is a django service with its own database to save definitions and
  crawling information
- The workers consist of the overall engine as well as the custom code per site to
  crawl and download from.

## Environment Setup
### Command to install dependencies
```bash
# production deps
pip install -r requirements.txt
```

### Environment Variables (Local dev environment)
```bash
cp sample.env .env
```

### Code formatting tools
- Install Black plugins for your favorite IDE using instructions from
[this link](https://black.readthedocs.io/en/stable/integrations/editors.html).
- Install pre-commit using steps [here](https://pre-commit.com/)


### Database Setup
After installing Postgres, create a new database. You should have the host, port, username,
password, and database name. Set the connection string to the database inside the `.env`
file you just created. Then, to set up the schema, run
```bash
./manage.py runserver
```

### Building the Docker image
In the command below, the BUILD_VERSION build argument is a mandatory requirement.
You can use any text here - you can leave it to default to dev as in the command below.
```bash
docker build -t plateiq/webedi --build-arg BUILD_VERSION=dev .
```

### Pulling the Docker image from ECR
If you don't want to bother building the image but just want to use the image, you can
simply pull the latest version from ECR.
```bash
docker pull 767512458197.dkr.ecr.us-east-1.amazonaws.com/plateiq/webedi:latest
```

## Executing
Running webedi using docker containers requires some environment variables to be set.
WEBEDI_ALLOW_LOCALHOST is only required for the development web server.

In addition, if you're running webedi in a container, AND running Postgres in a
different container, you will have to link the two containers.

### Running the web service / workers (locally)
For all commands below, you need to run them in a `virtualenv`, and set the
appropriate environment variables.
```bash
source venv/bin/activate

# set environment variables
export LOCAL_ENV=True
export DATABASE_URL=whatever
```

Running django management commands (workers are invoked using management commands):
```bash
./manage.py my_command

# so you'll setup the database using
./manage.py migrate
```

Running the web service
```bash
./manage.py runserver
```


### Running the web service / workers (Docker)
Running webedi using docker containers requires some environment variables to be set.
In addition, if you're running Postgres in a different container, you will have to link
the two containers.

In the examples below:
- Replace <postgres_container> with the id or name of your postgres container. This linking
  is only required if your database is in another container.
- WEBEDI_ALLOW_LOCALHOST is only required for development

Running the web service
```bash
docker run -it --rm -p 8001:5000 \
    --link piq-server-pg \
    -e LOCAL_ENV=True \
    -e DATABASE_URL="postgresql://username:password@piq-server-pg:5432/piq_webedi"
    plateiq/webedi
```

Running a worker (django management command):
```bash
docker run -it --rm \
    --link piq-server-pg \
    -e LOCAL_ENV=True \
    -e DATABASE_URL="postgresql://username:password@piq-server-pg:5432/piq_webedi"
    plateiq/webedi python3 manage.py my_command
```


## Contributing / Development Guidelines

### Version Control
All new changes to the repo should use the following workflow

- create new branch from master
- commit code to branch, push
- create pull request from branch to master
- merge once it has passed code review and tests


### Adding / Removing dependencies
`pip install stuff`

### Testing
All code we add should be accompanied by unit tests. Running tests:
```bash
./manage.py test
```

### Pylint
The CI pipeline (Jenkins) runs pylint on the codebase to warn about code smells etc.
It is configured to allow no new warnings other than already existing ones, otherwise
it fails builds.

Here's how you can (and should) run pylint locally, from your root directory:
```bash
pylint --rcfile=.pylintrc --output-format=colorized webedi
```


## Deployment
## Pushing Docker Image to ECR
WARNING: THIS WILL PUSH THE NEW IMAGE TO PRODUCTION AND DEPLOY. THIS IS MEANT
TO BE A REFERENCE ONLY, DON'T DO THIS FROM YOUR DEV ENVIRONMENT !

Once you have the latest docker image built, do the following

```bash
# tag to ECR
docker tag plateiq/webedi:latest 767512458197.dkr.ecr.us-east-1.amazonaws.com/plateiq/webedi:latest

# login to ECR
$(aws ecr get-login --no-include-email --region us-east-1)

# push to container repo
docker push 767512458197.dkr.ecr.us-east-1.amazonaws.com/plateiq/webedi:latest
```

## Deploy Service using Elastic Beanstalk
```bash
# deploy web service
# this assumes the eb application is initialized (eb init, etc.)
eb deploy plateiq/microwave
```

## Commands - Quick Reference

### Triggering ALL Jobs for ALL supported operations
Use the following command. This command also accepts params (see further examples for usages)
```shell
./manage.py trigger_jobs
```

### Triggering specific Jobs
The following command will smartly schedule jobs as necessary. If used without the `--created_via`
flag, this is idempotent (it won't create multiple runs even if you run it multiple times)
```shell
./manage.py trigger_jobs --operations "invoice.download,<op2>" --jobs "job_abc,job_xyz"
```

### Triggering specific Jobs without de-duplication scheduling
If you want to override checks, add a `--created_via`
```shell
./manage.py trigger_jobs --operations "invoice.download,<op2>" --jobs "job_abc,job_xyz" --created_via "admin"
```
