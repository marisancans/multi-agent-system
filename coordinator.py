import time
import random
import asyncio
import uuid
from spade.agent import Agent
from spade.behaviour import FSMBehaviour, State
import cv2
import numpy as np
import json
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour, OneShotBehaviour
from spade.message import Message
from collections import OrderedDict, deque

from drawing import update_positions, update_messages, update_packages, show

STATE_WAIT_TASK = "STATE_WAIT_TASK"
STATE_PICK_PACKAGE = "STATE_PICK_PACKAGE"
STATE_REPORT_BAD_PACKAGE = "STATE_REPORT_BAD_PACKAGE"
STATE_MOVING_PACKAGE = "STATE_MOVING_PACKAGE"
STATE_GIVE_PACKAGE_TO_INSPECTION = "STATE_GIVE_PACKAGE_TO_INSPECTION"
STATE_GO_TO_WAREHOUSE = "STATE_GO_TO_WAREHOUSE"

CENTRAL_AGENT_JID = "centralsistema@xmpp.jp"  # Jabber ID used in XMPP

NEW_PACKAGE_COEF = 0.99
PACKAGE_CAPACITY = 10
MESSAGES_CAPACITY = 10
BAD_PACKAGE_COEF = 0.3

packages = OrderedDict()
messages = deque(maxlen=11)
positions = {}
dropped = 0

start_time = time.time()

class CoordinatorAgent(Agent):

    class CheckNewPackagesBehav(PeriodicBehaviour):
        async def run(self):
            got_new_package = random.random()

            if got_new_package > NEW_PACKAGE_COEF:
                return

            if len(packages) > PACKAGE_CAPACITY:
                # print("Capacity reached, throwing out package!")
                return
            
            print('Got new package')

            packages[str(uuid.uuid4())[:8]] = {'status': 'UNSHIPPED', 'executor': ''}

        async def on_end(self):
            await self.agent.stop()

    class CheckMessagesBehav(PeriodicBehaviour):
        async def run(self):
            # Always wait for a task
            msg = await self.receive(timeout=5) # wait for a message for 10 seconds
            
            if msg:
                # print(f"Message: {msg.body}")
                time_passed = time.time() - start_time
                sender = msg.sender.localpart

                body = json.loads(msg.body)

                if body["action"] == "WAITING_FOR_TASK":
                    reply = msg.make_reply()
                    await self.asign_task(reply, sender, packages)
                
                if body["action"] == "MOVING":
                    positions[sender] = body["distance"]


                if body["action"] == "PACKAGE_DELIVERED":
                    reply = msg.make_reply()
                    reply.body = json.dumps({"action": "GO_TO_WAREHOUSE"})
                    await self.send(reply)
                    await self.delivered_package(sender)

                if body["action"] == "PACKAGE_DROPPED":
                    reply = msg.make_reply()
                    reply.body = json.dumps({"action": "GO_TO_WAREHOUSE"})
                    await self.send(reply)
                    await self.delivered_package(sender)

                if body["action"] == "PACKAGE_INSPECTED":
                    reply = msg.make_reply()
                    reply.body = json.dumps({"action": "GO_TO_WAREHOUSE"})
                    await self.send(reply)
                    await self.delivered_package(sender)
                    


                messages.append(f'{time_passed:.2f} | {sender} | {msg.body}')
            else:
                print("Did not received any message after 5 seconds")

        async def asign_task(self, reply: Message, sender: str, packages):
            package_aviable = False
            for k in list(packages.keys()):
                if not packages[k]['executor']:
                    packages[k]['executor'] = sender
                    packages[k]['status'] = 'MOVING'
                    package_aviable = True
                    break

            rnd = random.random()
            if rnd < BAD_PACKAGE_COEF:
                reply.body = json.dumps({"action": 'GO_TO_INSPECTION'})
                await self.send(reply)
                return
                

            if not package_aviable:
                return
            
            reply.body = json.dumps({"action": "GO_TO_TERMINAL"})
            await self.send(reply)

        async def delivered_package(self, sender):
            delete_me = []
            for pack_id, data in packages.items():
                if not 'executor' in data:
                    continue
                if data['executor'] == sender:
                    delete_me.append(pack_id)

            for id in delete_me:
                del packages[id]
    
    class DrawBehaw(PeriodicBehaviour):
        async def run(self):
            img_packages = update_packages(packages)
            img_messages = update_messages(messages)
            img_positions = update_positions(positions)

            img = np.concatenate([img_packages, img_messages], axis=1)
            img = np.concatenate([img, img_positions], axis=0)
            show('status', img, 1)
            
    async def setup(self):
        print(f"Coordinator started")
        b = self.CheckNewPackagesBehav(period=1)
        self.add_behaviour(b)

        b = self.CheckMessagesBehav(period=1)
        self.add_behaviour(b)

        b = self.DrawBehaw(period=1)
        self.add_behaviour(b)

        # b = self.AssignTaskBehav()
        # self.add_behaviour(b)



if __name__ == "__main__":
    agent = CoordinatorAgent("centralsistema@jix.im", "Parol3")
    agent.start()

    while True:
        time.sleep(1)