import tornado.httpserver
from tornado.options import (options,
    parse_command_line, define)
from tornado.websocket import WebSocketHandler
import tornado.ioloop
import tornado.web
import socket
import json
import os
import redis
import random
import ast

try:
    LOCAL = os.environ.get('LOCAL')
except:
    LOCAL = False

define("port", default=8888, help="run on the given port", type=int)

if not LOCAL:
    r = redis.from_url(os.environ.get("REDIS_URL"))
else:
    r = redis.StrictRedis(host='localhost', port=6379, db=0)

'''
This is a simple Websocket Echo server that uses the Tornado websocket handler.
Please run `pip install tornado` with python of version 2.7.9 or greater to install tornado.
This program will echo back the reverse of whatever it recieves.
Messages are output to the terminal for debuggin purposes. 
'''


class Game(object):

    rows = 15
    columns = 15
    win_count = 5
    win_cells = []

    def __init__(self,owner,opponent):
        self.owner = owner
        self.opponent = opponent

    def generate_game_field(self):
        grid = []
        for row in range(0,self.rows):
            columnArr = []
            for column in range(0,self.columns):
                cell = {
                    "x": column,
                    "y": row,
                    "state": None
                }
                columnArr.append(cell)
            grid.append(columnArr)
        self._game_field = grid

    def update_game_field_internal_owner(self,data):
        if not hasattr(self,'_game_field'):
            self.generate_game_field()
        x = data.get('x')
        y = data.get('y')
        cell = self._game_field[y][x]
        if not cell['state']:
            cell['state'] = self.owner['mark']
        opponent_game = self.opponent['connection'].game
        opponent_game.update_game_field_internal_opponent(data)

    def update_game_field_internal_opponent(self,data):
        if not hasattr(self,'_game_field'):
            self.generate_game_field()
        x = data.get('x')
        y = data.get('y')
        cell = self._game_field[y][x]
        if not cell['state']:
            cell['state'] = self.opponent['mark']

    def check_horizontal_axis(self,y,orig_x,x=None,count=1,reverse=False):
        row = self._game_field[y]
        if not reverse:
        
            if isinstance(x,type(None)):
                x = orig_x + 1
            else:
                x += 1
            if x >= len(row):
                reverse=True
                return self.check_horizontal_axis(y,orig_x,
                    x=None,reverse=reverse,count=count)
            else:
                if row[x]['state'] == self.owner['mark']:
                    count+=1
                    self.win_cells.append(row[x])
                    return self.check_horizontal_axis(y,orig_x,
                        x=x,reverse=reverse,count=count)
                else:
                    reverse = True
                    return self.check_horizontal_axis(y,orig_x,
                        x=None,reverse=reverse,count=count)
        else:

            if isinstance(x,type(None)):
                x = orig_x - 1
            else:
                x-=1
            if x < 0:
                if count >= self.win_count:
                    return self.win_cells
                else:
                    return False
            else:
                if row[x]['state'] == self.owner['mark']:
                    count+=1
                    self.win_cells.append(row[x])
                    return self.check_horizontal_axis(y,orig_x,
                        x=x,reverse=reverse,count=count)
                else:
                    if count >= self.win_count:
                        return self.win_cells
                    else:
                        return False

    def check_vertical_axis(self,x,orig_y,y=None,count=1,reverse=False):
        if not reverse:
        
            if isinstance(y,type(None)):
                y = orig_y + 1
            else:
                y += 1
            if y >= len(self._game_field):
                reverse=True
                return self.check_vertical_axis(x,orig_y,
                    y=None,reverse=reverse,count=count)
            else:
                if self._game_field[y][x]['state'] == self.owner['mark']:
                    count+=1
                    self.win_cells.append(self._game_field[y][x])
                    return self.check_vertical_axis(x,orig_y,
                        y=y,reverse=reverse,count=count)
                else:
                    reverse = True
                    return self.check_vertical_axis(x,orig_y,
                        y=None,reverse=reverse,count=count)
        else:

            if isinstance(y,type(None)):
                y = orig_y - 1
            else:
                y-=1
            if y < 0:
                if count >= self.win_count:
                    return self.win_cells
                else:
                    return False
            else:
                if self._game_field[y][x]['state'] == self.owner['mark']:
                    count+=1
                    self.win_cells.append(self._game_field[y][x])
                    return self.check_vertical_axis(x,orig_y,
                        y=y,reverse=reverse,count=count)
                else:
                    if count >= self.win_count:
                        return self.win_cells
                    else:
                        return False

    def check_second_diagonal(self,orig_x,orig_y,count=1,reverse=False,x=None,y=None):
        if not reverse:
            if isinstance(x,type(None)):
                x = orig_x + 1
                y = orig_y - 1
            else:
                x+=1
                y-=1
            if x == self.columns or y < 0:
                reverse = True
                return self.check_second_diagonal(orig_x,orig_y,
                    count=count,reverse=reverse,x=None,y=None)
            else:
                if self._game_field[y][x]['state'] == self.owner['mark']:
                    self.win_cells.append(self._game_field[y][x])
                    count+=1
                    return self.check_second_diagonal(orig_x,orig_y,
                        count=count,reverse=reverse,x=x,y=y)
                else:
                    reverse = True
                    return self.check_second_diagonal(orig_x,orig_y,
                        count=count,reverse=reverse,x=None,y=None)
        else:
            if isinstance(x,type(None)):
                x = orig_x - 1
                y = orig_y + 1
            else:
                x-=1
                y+=1
            if x < 0 or y == self.rows:
                if count >= self.win_count:
                    return self.win_cells
                else:
                    return False
            else:
                if self._game_field[y][x]['state'] == self.owner['mark']:
                    count+=1
                    self.win_cells.append(self._game_field[y][x])
                    return self.check_second_diagonal(orig_x,orig_y,
                        count=count,reverse=reverse,x=x,y=y)
                else:
                    if count >= self.win_count:
                        return self.win_cells
                    else:
                        return False

    def check_first_diagonal(self,orig_x,orig_y,count=1,reverse=False,x=None,y=None):
        if not reverse:
            if isinstance(x,type(None)):
                x = orig_x + 1
                y = orig_y + 1
            else:
                x+=1
                y+=1
            if x >= self.columns or y >= self.rows:
                reverse = True
                return self.check_first_diagonal(orig_x,orig_y,count=count,
                    reverse=reverse,x=None,y=None)
            else:
                if self._game_field[y][x]['state'] == self.owner['mark']:
                    count+=1
                    self.win_cells.append(self._game_field[y][x])
                    return self.check_first_diagonal(orig_x,orig_y,
                        count=count,reverse=reverse,x=x,y=y)
                else:
                    reverse = True
                    return self.check_first_diagonal(orig_x,orig_y,
                        count=count,reverse=reverse,x=None,y=None)
        else:
            if isinstance(x,type(None)):
                x = orig_x - 1
                y = orig_y - 1
            else:
                x-=1
                y-=1
            if x < 0 or y < 0:
                if count >= self.win_count:
                    return self.win_cells
                else:
                    return False
            else:
                if self._game_field[y][x]['state'] == self.owner['mark']:
                    count+=1
                    self.win_cells.append(self._game_field[y][x])
                    return self.check_first_diagonal(orig_x,orig_y,
                        count=count,reverse=reverse,x=x,y=y)
                else:
                    if count >= self.win_count:
                        return self.win_cells
                    else:
                        return False
        
    def check_diagonal(self,x,y):
        first = self.check_first_diagonal(x,y)
        if isinstance(first,list):
            return first
        else:
            self.win_cells = []
        second = self.check_second_diagonal(x,y)
        if isinstance(second,list):
            return second
        else:
            self.win_cells = []
        return False

    def check_win_condition(self,data):
        x = data.get('x')
        y = data.get('y')
        self.win_cells = []
        
        horizontal = self.check_horizontal_axis(y,x)
        if isinstance(horizontal,list):
            return horizontal
        else:
            self.win_cells = []
        vertical = self.check_vertical_axis(x,y)
        if isinstance(vertical,list):
            return vertical
        else:
            self.win_cells = []
        diagonal = self.check_diagonal(x,y)
        if isinstance(diagonal,list):
            return diagonal
        else:
            self.win_cells = []
        return False

class DataAdapter(object):

    @classmethod
    def get_leaderboard(cls):
        final_arr = []
        byte_dict = r.hgetall('leaderboard')
        for key, value in byte_dict.items():
            data = {
                "username":key.decode('utf-8')
                }
            data.update(ast.literal_eval(value.decode('utf-8')))
            final_arr.append(data)
        return final_arr

    @classmethod
    def increment_wins(cls,instance):
        value = r.hget('leaderboard', instance.get('username'))
        data = ast.literal_eval(value.decode('utf-8'))
        data['wins'] += 1
        r.hset('leaderboard', instance.get('username'),data)

    @classmethod
    def increment_moves(cls,instance):
        value = r.hget('leaderboard', instance.get('username'))
        data = ast.literal_eval(value.decode('utf-8'))
        data['moves'] += 1
        r.hset('leaderboard', instance.get('username'),data)

    @classmethod
    def check_create_user_for_leaderboards(cls,instance):
        if not r.hexists('leaderboard', instance.get('username')):
            data = {
                "wins":0,
                "moves":0
            }
            r.hset('leaderboard',instance.get('username'),data)

class WSHandler(WebSocketHandler):


    _on_close_called = False
    _registry = []
    adapter = DataAdapter

    def __init__(self,*args,**kwargs):
        self._registry.append({"connection":self})
        super(WebSocketHandler,self).__init__(*args,**kwargs)

    def open(self):
        self.connection_closed = False
        leaderboard = self.adapter.get_leaderboard()
        self.write_message(\
            {
                'type':'leaderboard',
                'content':leaderboard
            })

    @property
    def registry_instance_for_self(self):
        if not hasattr(self,'_registy_instance_for_self'):
            for registry_instance in self._registry:
                if registry_instance.get('connection') == self:
                    self._registy_instance_for_self = registry_instance
                    return registry_instance
        else:
            return self._registy_instance_for_self

    def find_registry_instance_with_empty_game_state(self):
        for registry_instance in self._registry:
            if registry_instance.get('state') == 'empty' and registry_instance.get('connection') != self:
                return registry_instance
        return False

    def game_initialize(self,second_user_instance):
        own_instance = self.registry_instance_for_self
        own_instance['state'] = 'playing'
        second_user_instance['state'] = 'playing'
        self.adapter.check_create_user_for_leaderboards(own_instance)
        self.adapter.check_create_user_for_leaderboards(second_user_instance)

        tie = int(random.random()*100)
        if tie < 49:
            move_first = True
            move_second = False
            mark_first = 'X'
            mark_second = 'O'
        else:
            move_first = False
            move_second = True
            mark_first = 'X'
            mark_second = 'O'
        own_instance['move'] = move_first
        second_user_instance['move'] = move_second
        own_instance['mark'] = mark_first
        second_user_instance['mark'] = mark_second
        own_connection = own_instance.get('connection')
        leaderboard = self.adapter.get_leaderboard()
        own_connection.write_message(
            {
                "type":"game_start",
                "content": {
                    "opponent":second_user_instance.get('username'),
                    "move":move_first,
                    "mark":mark_first,
                    "leaderboard":leaderboard
                }
            })

        second_user_connection = second_user_instance.get('connection')
        second_user_connection.write_message(
            {
                "type":"game_start",
                "content": {
                    "opponent":own_instance.get('username'),
                    "move":move_second,
                    "mark":mark_second,
                    "leaderboard":leaderboard
                }
            })
        self.game = Game(own_instance,second_user_instance)
        second_user_instance.get('connection').game = Game(second_user_instance,own_instance)

    def new_user(self,data):
        instance = self.registry_instance_for_self
        instance['username'] = data
        instance['state'] = 'empty'
        second_player_instance = self.find_registry_instance_with_empty_game_state()
        if isinstance(second_player_instance,dict):
            self.game_initialize(second_player_instance)

    def user_move(self,data):
        game = self.game
        own_instance = self.game.owner
        opponent_instance = self.game.opponent
        game.update_game_field_internal_owner(data)
        self.adapter.increment_moves(own_instance)
        win = game.check_win_condition(data)
        if not isinstance(win,list):
            leaderboard = self.adapter.get_leaderboard()
            opponent_instance['move'] = True
            own_instance['move'] = False
            opponent_instance.get('connection').write_message({
                    "type":"user_move",
                    "content": {
                        "cell": data,
                        "move": True,
                        "leaderboard":leaderboard
                    }
                })
            own_instance.get('connection').write_message({
                    "type":"user_move",
                    "content": {
                        "move":False,
                        "leaderboard":leaderboard
                    }
                })
        else:
            win.append(data)
            self.adapter.increment_wins(own_instance)
            leaderboard = self.adapter.get_leaderboard()
            opponent_instance.get('connection').write_message({
                    "type":"game_over",
                    "content": {
                        "won": False,
                        "cell": data,
                        "leaderboard":leaderboard,
                        "winning_cells":win
                    }
                })
            own_instance.get('connection').write_message({
                    "type":"game_over",
                    "content": {
                        "won": True,
                        "leaderboard":leaderboard,
                        "winning_cells":win
                    }
                })

    def play_again(self,data):
        second_user = self.game.opponent
        self.game_initialize(second_user)

    def end_game(self,blank):
        self.cleanup()

    def write_message_with_precheck(self,data):
        if not self.connection_closed:
            self.write_message(data)

    def switch_user(self,data):
        new_username = data.get('new_username')
        own_instance = self.registry_instance_for_self
        own_instance['username'] = new_username
        if hasattr(self,'game') and not isinstance(self.game,type(None)):
            opponent = self.game.opponent
            opponent.get('connection').write_message_with_precheck({
                "type":"end_game"
            })
            self.write_message_with_precheck({
                "type":"end_game"
            })
        else:
            own_instance['state'] = 'empty'
            second_player_instance = self.find_registry_instance_with_empty_game_state()
            if isinstance(second_player_instance,dict):
                self.game_initialize(second_player_instance)

    def cleanup(self):
        try:
            if hasattr(self,'game') and not isinstance(self.game,type(None)):
                opponent = self.game.opponent
                own_instance = self.game.owner
                opponent['state'] = 'empty'
                opponent.get('connection').game = None
                own_instance['state'] = 'empty'
                own_instance.get('connection').game = None
                opponent.get('connection').write_message_with_precheck({
                    "type":"end_game"
                    })
                self.write_message_with_precheck({
                    "type":"end_game"
                    })
        except Exception as exc:
            raise exc

    def on_message(self, message):
        print(message)
        self.connection_closed = False
        if isinstance(message,bytes):
            message = message.decode('utf-8')
        json_dict = json.loads(message)
        if hasattr(self,json_dict.get('type')):
            method = getattr(self,json_dict.get('type'))
            method(json_dict.get('content'))

    def on_close(self):
        self.connection_closed = True
        self.cleanup()
        instance = self.registry_instance_for_self
        index = self._registry.index(instance)
        self._registry.pop(index)
 
    def check_origin(self, origin):
        return True

def make_app():
    application = tornado.web.Application([
        (r'/', WSHandler),
    ])
    return application

if __name__ == "__main__":
    parse_command_line()
    http_server = tornado.httpserver.HTTPServer(make_app())
    http_server.listen(options.port)
    print('running...')
    tornado.ioloop.IOLoop.instance().start()
 