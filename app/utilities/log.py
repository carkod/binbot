import logging
from utilities.environment import API_URL

is_production = API_URL.BINBOARD_PROD_ENV
is_development = API_URL.BINBOARD_DEV_ENV

def logger(text):
    if is_production:
        filemode = 'a'
    else:
        filemode = 'w'

    logging.basicConfig(filename='signal.log',filemode=filemode,format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',datefmt='%H:%M:%S',level=logging.INFO)
    logging.info(text)
    logging.getLogger('signal-level')