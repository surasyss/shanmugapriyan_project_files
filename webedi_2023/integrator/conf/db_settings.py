import environ

env = environ.Env()

DATABASE_ENV = "DATABASE_URL"

DATABASES = {
    "default": env.db(
        DATABASE_ENV, default="postgresql://piq_dbadmin:password@127.0.0.1:5432/webedi"
    ),
}
