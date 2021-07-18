from cchess import ChessBoard,FULL_INIT_FEN,Move
import re,logging,traceback,sys


class GameKeeper():
    def __init__(self,groupId):
        self.startWith=FULL_INIT_FEN
        #self.board=ChessBoard(self.startWith)
        self.board=ChessBoard('4k4/3ca4/4b4/3c5/9/9/9/4B4/3CAC3/4K4 w - - 0 1')
        self.last_checked = False
        self.move_history = []
        self.groupId=groupId
        self.players=[]


    def move_chinese(self,move_str):
        move_str = lazy_move(move_str)
        if move_str=='':
            return (0,None)
        try:
            move_from, move_to = Move.from_chinese(self.board, move_str)
        except Exception as ex:
            traceback.print_exc(file=sys.stdout)
            return (0,'选子错误。')
            #return False

        if not self.board.is_valid_move(move_from, move_to):
            return (0,'走法错误。')
            #return False
        
        check_count = self.board.is_checked_move(move_from, move_to)
        if check_count:
            if self.last_checked:
                return (0,"必须应将。")
            else:
                return (0,"不能送将。")

        move = self.board.move(move_from, move_to)
        print(move.to_chinese())
        self.board.next_turn()

        move.for_ucci(self.board.move_side, self.move_history)
        self.move_history.append(move)

        if self.board.is_dead():
            return (3, "将死！")
            #return (3, None)

        self.last_checked = self.board.is_checked()
        if self.last_checked:
            print(u"将军！")
            return (self.board.move_side.value, "将军！")

        if move.is_king_killed():
            return (3, "杀死！")
            #return (3, None)
        
        return (self.board.move_side.value,None)
    def regret(self,regret_player,step):
        #悔棋
        allSteps=len(self.move_history)
        if allSteps%2 != regret_player:
            allSteps+=1
        toStep=allSteps-step*2
        self.board=self.move_history[toStep].board.copy()
        self.move_history=self.move_history[:toStep]


    def moving_player(self):
        return self.players[self.board.move_side.value - 1]

    def dump_board(self,board_type):
        return self.board.dump_board_compact(board_type)


indexes=('１', '２', '３', '４', '５', '６', '７', '８', '９',
         '1','2','3','4','5','6','7','8','9',
         '一', '二', '三', '四', '五', '六', '七','八', '九')
moves=(('j','p','t'),('进','平','退'))
pieces={'k': "帅",'s': "士",'x': "象",'m': "马",'j': "车",'c': "车",'p': "炮",'b': "兵",'z': "卒",'q':'前','h':'后'}

def lazy_move(move_str):
    if not len(move_str)==4:
        return ''
    if not move_str[3] in indexes:
        print(2222)
        return ''
    move_str=[s for s in move_str]
    try:
        i=moves[0].index(move_str[2].lower())
        move_str[2]=moves[1][i]
    except:
        if not move_str[2] in moves[1]:
            print(1111)
            return ''
    for i in range(2):
        try:
            move_str[i]=pieces[move_str[i].lower()]
        except:
            pass
    print(move_str)
    return ''.join(move_str)

    