# import logging.handlers
# import datetime
# #from ..lib.global_var import *
#
# def userlog(username):
#     '''
#     logger = logging.getLogger('mylogger')
#     logger.setLevel(logging.DEBUG)
#
#     rf_handler = logging.handlers.TimedRotatingFileHandler(log_user_dir)
#     #rf_handler = logging.handlers.TimedRotatingFileHandler(log_user_dir, when='midnight', interval=1, backupCount=7, atTime=datetime.time(0, 0, 0, 0))
#
#     rf_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s - " + username))
#
#     f_handler = logging.FileHandler(log_error_dir)
#     f_handler.setLevel(logging.ERROR)
#     f_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(filename)s[:%(lineno)d] - %(message)s - " + username))
#
#     logger.addHandler(rf_handler)
#     logger.addHandler(f_handler)
#     '''
#     logger = logging.getLogger(__name__)
#     logger.setLevel(level=logging.DEBUG)
#     handler = logging.FileHandler("user.log")
#     handler.setLevel(logging.DEBUG)
#     formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s - ' + username)
#     handler.setFormatter(formatter)
#     logger.addHandler(handler)
#     return logger
#
# '''
# logger = userlog('lezhang')
# logger.debug('debug test message.....')
#
# logger.info('info test message')
# logger.warning('warning test message')
# logger.error('error test message')
# logger.critical('critical test message')
# '''
