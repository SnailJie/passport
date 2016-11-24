#!/usr/bin/python -O
#product environment start application with `tornado IOLoop` and `gevent server`

from main import app
from utils.tool import logger
from config import GLOBAL, PRODUCT

Host = GLOBAL.get('Host')
Port = GLOBAL.get('Port')
Environment = GLOBAL.get('Environment')
ProcessName = PRODUCT.get('ProcessName')
ProductType = PRODUCT.get('ProductType')

try:
    import setproctitle
except ImportError, e:
    logger.warn("%s, try to pip install setproctitle, otherwise, you can't use the process to customize the function" %e)
else:
    setproctitle.setproctitle(ProcessName)
    logger.info("The process is %s" % ProcessName)

try:
    msg = '%s has been launched, %s:%s' %(ProcessName, Host, Port)
    print(msg)
    logger.info(msg)
    if ProductType == 'gevent':
        from gevent.wsgi import WSGIServer
        http_server = WSGIServer((Host, Port), app)
        http_server.serve_forever()

    elif ProductType == 'tornado':
        from tornado.wsgi import WSGIContainer
        from tornado.httpserver import HTTPServer
        from tornado.ioloop import IOLoop
        http_server = HTTPServer(WSGIContainer(app))
        http_server.listen(Port)
        IOLoop.instance().start()

    else:
        msg = 'Start the program does not support with %s, abnormal exit!' %ProductType
        logger.error(msg)
        raise RuntimeError(msg)

except Exception,e:
    print(e)
    logger.error(e, exc_info=True)
