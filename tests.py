import server as server_under_test
from tornado.testing import AsyncHTTPTestCase, gen_test, main
from tornado.websocket import websocket_connect
from tornado import httpserver, testing, gen
import json
from tornado.ioloop import TimeoutError
import time

class TestHelloApp(AsyncHTTPTestCase):

	def get_app(self):
		self.app = server_under_test.make_app()
		return self.app

	def tearDown(self):
		self.handler._registry = []

	def setUp(self):
		super(TestHelloApp, self).setUp()
		server = httpserver.HTTPServer(self.app)
		socket, self.port = testing.bind_unused_port()
		server.add_socket(socket)
		self.handler = server_under_test.WSHandler

	def _mk_connection(self):
		return websocket_connect(
			'ws://localhost:{}/'.format(self.port),
			io_loop = self.io_loop
		)

	@gen.coroutine
	def _mk_client(self):
		c = yield self._mk_connection()
		_ = yield c.read_message()
		raise gen.Return(c)

	@gen_test
	def test_websocket_open(self):
		self.assertEqual(self.handler._registry,[])
		c = yield self._mk_connection()
		response = yield c.read_message()
		data = {"type":"new_user","content":"user"}
		c.write_message(json.dumps(data))
		self.assertEqual('leaderboard', json.loads(response)['type'])
		response = c.close(code=1000)
		yield gen.sleep(2)
		self.assertEqual(self.handler._registry,[])

	@gen_test
	def test_websocket_close(self):
		self.assertEqual(self.handler._registry,[])
		c = yield self._mk_client()
		data = {"type":"new_user","content":"userXXX"}
		_ = yield c.write_message(json.dumps(data))
		yield gen.sleep(2)
		handler = server_under_test.WSHandler
		records = []
		for record in handler._registry:
			if record.get('username',None) == 'userXXX':
				records.append(record)
		self.assertEqual(len(records),1)
		response = c.close(code=1000)
		yield gen.sleep(2)
		records = []
		for record in handler._registry:
			if record.get('username',None) == 'userXXX':
				records.append(record)
		self.assertEqual(len(records),0)

	@gen_test
	def test_pick_username(self):
		self.assertEqual(self.handler._registry,[])
		c = yield self._mk_client()
		data = {"type":"new_user","content":"user1"}
		_ = yield c.write_message(json.dumps(data))
		yield gen.sleep(2)
		handler = server_under_test.WSHandler
		records = []
		for record in handler._registry:
			if record.get('username',None) == 'user1':
				records.append(record)
		self.assertEqual(len(records),1)
		self.assertEqual(records[0]['state'],'empty')
		response = c.close(code=1000)
		yield gen.sleep(2)
		self.assertEqual(handler._registry,[])

	@gen_test(timeout=15)
	def test_two_pick_username(self):
		self.assertEqual(self.handler._registry,[])
		c = yield self._mk_client()
		c1 = yield self._mk_client()
		data = {"type":"new_user","content":"user1"}
		data2 = {"type":"new_user","content":"user2"}
		_ = yield c.write_message(json.dumps(data))
		yield gen.sleep(2)
		_ = yield c1.write_message(json.dumps(data2))
		yield gen.sleep(2)
		response = yield c.read_message()
		response2 = yield c1.read_message()
		result1 = json.loads(response)
		self.assertEqual(result1['type'],'game_start')
		result2 = json.loads(response2)
		self.assertEqual(result2['type'],'game_start')
		c.close(code=1000)
		yield gen.sleep(2)
		c1.close(code=1000)
		yield gen.sleep(2)
		self.assertEqual(self.handler._registry,[])

	@gen_test(timeout=15)
	def test_end_game(self):
		self.assertEqual(self.handler._registry,[])
		c = yield self._mk_client()
		c1 = yield self._mk_client()
		data = {"type":"new_user","content":"user1"}
		data2 = {"type":"new_user","content":"user2"}
		_ = yield c.write_message(json.dumps(data))
		yield gen.sleep(2)
		_ = yield c1.write_message(json.dumps(data2))
		yield gen.sleep(2)
		response = yield c.read_message()
		response2 = yield c1.read_message()
		data3 = {"type":"end_game","content":""}
		_ = yield c.write_message(json.dumps(data3))
		yield gen.sleep(2)
		response = yield c.read_message()
		response2 = yield c1.read_message()
		result1 = json.loads(response)
		result2 = json.loads(response2)
		self.assertEqual(result1['type'],'end_game')
		self.assertEqual(result2['type'],'end_game')
		c.close(code=1000)
		c1.close(code=1000)
		yield gen.sleep(2)
		self.assertEqual(self.handler._registry,[])

	@gen_test(timeout=20)
	def test_switch_user_and_start_new_game(self):
		self.assertEqual(self.handler._registry,[])
		c = yield self._mk_client()
		c1 = yield self._mk_client()
		data = {"type":"new_user","content":"user1"}
		data2 = {"type":"new_user","content":"user2"}
		_ = yield c.write_message(json.dumps(data))
		yield gen.sleep(2)
		_ = yield c1.write_message(json.dumps(data2))
		yield gen.sleep(2)
		response = yield c.read_message()
		response2 = yield c1.read_message()
		data3 = {"type":"switch_user","content":{"username":"john"}}
		_ = yield c.write_message(json.dumps(data3))
		yield gen.sleep(2)
		response = yield c.read_message()
		response2 = yield c1.read_message()
		result1 = json.loads(response)
		result2 = json.loads(response2)
		self.assertEqual(result1['type'],'end_game')
		self.assertEqual(result2['type'],'end_game')

		# try to push play again

		data_play1 = {"type":"play_again","content":[]}
		_ = yield c1.write_message(json.dumps(data_play1))
		yield gen.sleep(2)
		response = yield c.read_message()
		response2 = yield c1.read_message()
		result1 = json.loads(response)
		self.assertEqual(result1['type'],'game_start')
		result2 = json.loads(response2)
		self.assertEqual(result2['type'],'game_start')

		c.close(code=1000)
		yield gen.sleep(2)

		# check that the second user is set to 'empty'
		# and has no game.
		response2 = yield c1.read_message()
		result2 = json.loads(response2)
		self.assertEqual(result2['type'],'end_game')
		self.assertEqual(len(self.handler._registry),1)
		self.assertEqual(self.handler._registry[0]['state'],'empty')

		c1.close(code=1000)
		yield gen.sleep(2)
		self.assertEqual(self.handler._registry,[])


