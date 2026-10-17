import http.client
import unittest
from tests import test_http

class LanAuthorityTests(unittest.TestCase):
    setUp = test_http.HttpTests.setUp
    tearDown = test_http.HttpTests.tearDown
    def test_explicit_lan_host_and_origin(self):
        def request(host,origin=None):
            c=http.client.HTTPConnection('127.0.0.1',self.server.server_port)
            headers={'Host':host}
            if origin: headers['Origin']=origin
            c.request('GET','/api/bootstrap',headers=headers)
            r=c.getresponse();status=r.status;r.read();c.close();return status
        host=f'192.168.1.20:{self.server.server_port}'
        self.assertEqual(request(host),403)
        self.server.allowed_hosts=('192.168.1.20',)
        self.assertEqual(request(host,'http://'+host),200)
        self.assertEqual(request(host,'http://evil.example'),403)
        self.assertEqual(request(f'192.168.1.21:{self.server.server_port}'),403)
