from spices.django3.conf.env_settings import *  # pylint: disable=wildcard-import,unused-wildcard-import

APP_NAME = env.str("APP_NAME", "webedi-local" if LOCAL_ENV else "webedi-nonlocal")
