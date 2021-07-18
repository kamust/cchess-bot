from graia.broadcast import Broadcast
from graia.application import GraiaMiraiApplication, Session
from graia.application.message.chain import MessageChain
import asyncio, json
from graia.application.message.elements.internal import Plain, At, Source
from graia.application.friend import Friend
from graia.application.group import Group, Member

from graia.broadcast.interrupt import InterruptControl
from graia.broadcast.interrupt.waiter import Waiter
from graia.application.event.messages import GroupMessage

from game import GameKeeper

games = {}

# 机器人qq号
botId = 123456789

loop = asyncio.get_event_loop()
bcc = Broadcast(loop=loop)
app = GraiaMiraiApplication(
    broadcast=bcc,
    connect_info=Session(
        host="http://localhost:25634",  # 填入 httpapi 服务运行的地址
        authKey="authKey",  # 填入 authKey
        account=botId,  # 你的机器人的 qq 号
        websocket=True  # Graia 已经可以根据所配置的消息接收的方式来保证消息接收部分的正常运作.
    )
)
inc = InterruptControl(bcc)

with open('helps.json','r',encoding='utf-8') as fp:
    helps=json.loads(fp.read())

@bcc.receiver("GroupMessage")
async def move_by_chinese(message: MessageChain, app: GraiaMiraiApplication, group: Group, member: Member):
    if not (group.id in games and message.has(Plain) and member.id == games[group.id].moving_player()):
        return
    messagetext = message[Plain][0].text.replace(' ', '')
    moving_side, info = games[group.id].move_chinese(messagetext)
    if moving_side:
        if moving_side == 1:
            m1 = MessageChain.create(
                [Plain('轮到红方走棋'), At(games[group.id].players[0])])
        elif moving_side == 2:
            m1 = MessageChain.create(
                [Plain('轮到黑方走棋'), At(games[group.id].players[1])])
        elif moving_side == 3:
            m1 = MessageChain.create([Plain(info+',本局结束')])
        m1.plus(MessageChain.create([Plain('\n'+s) for s in games[group.id].dump_board(0)]))
        await app.sendGroupMessage(group, m1)
        if moving_side == 3:
            del games[group.id]
            return
    if info:
        await app.sendGroupMessage(group, MessageChain.create([Plain(info)]))


@bcc.receiver("GroupMessage")
async def start_game(message: MessageChain, app: GraiaMiraiApplication, group: Group, member: Member):
    if not message.has(Plain):
        return
    if message[Plain][0].text.replace(' ', '').startswith("开始象棋"):
        if group.id in games:
            await app.sendGroupMessage(group, MessageChain.create([Plain("本群已经存在一个棋局")]),quote=message[Source][0])
        else:
            games[group.id] = GameKeeper(group.id)
            if not set_players(message, group.id):
                await app.sendGroupMessage(group, MessageChain.create([Plain("请通过@选择对局双方")]),quote=message[Source][0])
                @Waiter.create_using_function([GroupMessage])
                def waiter(event: GroupMessage, waiter_group: Group, waiter_member: Member, waiter_message: MessageChain):
                    if all([waiter_group.id == group.id, waiter_member.id == member.id]):
                        if set_players(waiter_message, group.id):
                            return True
                        return False
                if not await inc.wait(waiter):
                    del games[group.id]
                    await app.sendGroupMessage(group, MessageChain.create([Plain("创建失败")]))
                    return
            m1 = MessageChain.create(
                [Plain('请红方开始'), At(games[group.id].players[0])])
            m1.plus(MessageChain.create([Plain('\n'+s) for s in games[group.id].dump_board(0)]))
            # await app.sendGroupMessage(group, MessageChain.create([Plain('对局双方: \n'+str(games[group.id].players[0])+'\n'+str(games[group.id].players[1]))]))
            await app.sendGroupMessage(group, m1)


def set_players(message, groupId):
    if not message.has(At):
        return False
    if len(message[At]) != 2:
        return False
    games[groupId].players = []
    for a in message[At]:
        if a.target == botId:
            return False
        games[groupId].players.append(a.target)
    return True

@bcc.receiver("GroupMessage")
async def regret_chess(message: MessageChain, app: GraiaMiraiApplication, group: Group, member: Member):
    if not (group.id in games and message.has(Plain) and member.id in games[group.id].players):
        return
    if message[Plain][0].text.replace(' ', '').startswith("悔棋"):
        regret_player=games[group.id].players.index(member.id)
        opposite_id=games[group.id].players[1-regret_player]
        await app.sendGroupMessage(group, MessageChain.create([At(opposite_id),Plain("对方申请悔棋，是否同意？发送“同意”或其他任意字符拒绝")]),quote=message[Source][0])
        @Waiter.create_using_function([GroupMessage])
        def waiter(event: GroupMessage, waiter_group: Group, waiter_member: Member, waiter_message: MessageChain):
            if all([waiter_group.id == group.id, waiter_member.id == opposite_id]):
                if waiter_message.asDisplay().startswith("同意"):
                    return True
                return False
        if await inc.wait(waiter):
            games[group.id].regret(regret_player,1)
            m1 = MessageChain.create([Plain('同意悔棋')])
            m1.plus(MessageChain.create([Plain('\n'+s) for s in games[group.id].dump_board(0)]))
            await app.sendGroupMessage(group, m1)



@bcc.receiver("GroupMessage")
async def quit_game(message: MessageChain, app: GraiaMiraiApplication, group: Group, member: Member):
    if not (group.id in games and message.has(Plain) and member.id in games[group.id].players):
        return
    if message[Plain][0].text.replace(' ', '').startswith("退出"):
        await app.sendGroupMessage(group, MessageChain.create([Plain("是否确认退出？发送“确认”或其他任意字符取消")]),quote=message[Source][0])
        @Waiter.create_using_function([GroupMessage])
        def waiter(event: GroupMessage, waiter_group: Group, waiter_member: Member, waiter_message: MessageChain):
            if all([waiter_group.id == group.id, waiter_member.id == member.id]):
                if waiter_message.asDisplay().startswith("确认"):
                    return True
                return False
        if await inc.wait(waiter):
            await app.sendGroupMessage(group, MessageChain.create([Plain("玩家退出,本局结束")]))
            del games[group.id]

@bcc.receiver("GroupMessage")
async def helper(message: MessageChain, app: GraiaMiraiApplication, group: Group, member: Member):
    if not (message.has(At) and message[At][0].target==botId):
        return
    if not message.has(Plain):
        messagetext = '帮助'
    else:
        messagetext = message[Plain][0].text.replace(' ', '')
        if messagetext=='':
            messagetext = '帮助'
    if messagetext in helps:
        await app.sendGroupMessage(group, MessageChain.create([Plain(helps[messagetext])]),quote=message[Source][0])


app.launch_blocking()
