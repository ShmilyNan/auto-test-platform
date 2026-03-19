from core.config import settings
import secrets
# from config.constants import *


if __name__ == '__main__':
    print(secrets.token_urlsafe(64))
    # print(settings.APP_NAME)