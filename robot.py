import time
import random
import asyncio
import json
from spade.agent import Agent
from spade.message import Message
from spade.behaviour import FSMBehaviour, State
import argparse


STATE_WAIT_TASK = "STATE_WAIT_TASK"
STATE_GO_TO_TERMINAL = "STATE_GO_TO_TERMINAL"
STATE_GO_TO_WAREHOUSE = "STATE_GO_TO_WAREHOUSE"
STATE_DELIVER_PACKAGE = "STATE_DELIVER_PACKAGE"
STATE_PACKAGE_DROPPED = "STATE_PACKAGE_DROPPED"
STATE_GO_TO_INSPECTION = "STATE_GO_TO_INSPECTION"
STATE_PACKAGE_INSPECTED = "STATE_PACKAGE_INSPECTED"

STATE_GIVE_PACKAGE_TO_INSPECTION = "STATE_GIVE_PACKAGE_TO_INSPECTION"

DROP_CHANCE = 0.1
CENTRAL_AGENT_JID = "centralsistema@jix.im"  # Jabber ID used in XMPP  centralsistema@xmpp.jp


class ExampleFSMBehaviour(FSMBehaviour):
    async def on_start(self):
        print(f"FSM starting at initial state {self.current_state}")

    async def on_end(self):
        print(f"FSM finished at state {self.current_state}")
        await self.agent.stop()

class StateWaitForTask(State):
    async def run(self):
        print("I'm waiting for a task")

        msg = Message(to=CENTRAL_AGENT_JID)
        msg.body = json.dumps({"action": "WAITING_FOR_TASK"})
        await self.send(msg)

        # Always wait for a task
        msg = await self.receive(timeout=5) # wait for a message for 10 seconds
        
        if msg:
            print(f"Message received with content: {msg.body}")
            body = json.loads(msg.body)
            if body["action"] == "GO_TO_TERMINAL":
                self.set_next_state(STATE_GO_TO_TERMINAL)
            if body["action"] == "GO_TO_WAREHOUSE":
                self.set_next_state(STATE_GO_TO_WAREHOUSE)
            if body["action"] == "GO_TO_INSPECTION":
                self.set_next_state(STATE_GO_TO_INSPECTION)
        else:
            print("Did not received any message after 5 seconds")   
            self.set_next_state(STATE_WAIT_TASK)

async def moving(cb, destination, drop_chance=0):
    length = 5

    for i in range(5):
        msg = Message(to=CENTRAL_AGENT_JID)

        rnd = random.random()
        if rnd < drop_chance:
            # Whoopsy, dropped the package
            return True
        else:
            msg.body = json.dumps({"action": "MOVING", "destination": destination, "distance": round(i / length, 2)})
        
        await cb(msg)
        time.sleep(1)
    return False

class StateDeliverPackage(State):
    async def run(self):
        msg = Message(to=CENTRAL_AGENT_JID)
        msg.body = json.dumps({"action": "PACKAGE_DELIVERED"})
        await self.send(msg)

        # Go back to warehouse
        self.set_next_state(STATE_WAIT_TASK)

class StatePackageDropped(State):
    async def run(self):
        msg = Message(to=CENTRAL_AGENT_JID)
        msg.body = json.dumps({"action": "PACKAGE_DROPPED"})
        await self.send(msg)

        # Go back to warehouse
        self.set_next_state(STATE_WAIT_TASK)

class StateGoToWarehouse(State):
    async def run(self):
        # Move back to warehouse
        is_dropped = await moving(self.send, "warehouse")
        self.set_next_state(STATE_WAIT_TASK)

class StateGoToTerminal(State):
    async def run(self):
        # Move the package with a chance of dropping it
        is_dropped = await moving(self.send, "terminal", drop_chance=DROP_CHANCE)

        msg = Message(to=CENTRAL_AGENT_JID)
        if is_dropped:
            self.set_next_state(STATE_PACKAGE_DROPPED)
        else:
            self.set_next_state(STATE_DELIVER_PACKAGE)

class StateGoToInspection(State):
    async def run(self):
        is_dropped = await moving(self.send, "inspection")
        self.set_next_state(STATE_PACKAGE_INSPECTED)

class StatePackageInspected(State):
    async def run(self):
        msg = Message(to=CENTRAL_AGENT_JID)
        msg.body = json.dumps({"action": "PACKAGE_INSPECTED"})
        await self.send(msg)

        self.set_next_state(STATE_WAIT_TASK)




class RobotAgent(Agent):
    async def setup(self):
        fsm = ExampleFSMBehaviour()
        fsm.add_state(name=STATE_WAIT_TASK, state=StateWaitForTask(), initial=True)
        fsm.add_state(name=STATE_DELIVER_PACKAGE, state=StateDeliverPackage())

        fsm.add_state(name=STATE_GO_TO_TERMINAL, state=StateGoToTerminal())
        fsm.add_state(name=STATE_GO_TO_WAREHOUSE, state=StateGoToWarehouse())
        fsm.add_state(name=STATE_PACKAGE_DROPPED, state=StatePackageDropped())
        fsm.add_state(name=STATE_GO_TO_INSPECTION, state=StateGoToInspection())
        fsm.add_state(name=STATE_PACKAGE_INSPECTED, state=StatePackageInspected())

        fsm.add_transition(source=STATE_WAIT_TASK, dest=STATE_WAIT_TASK)
        fsm.add_transition(source=STATE_WAIT_TASK, dest=STATE_GO_TO_TERMINAL)
        fsm.add_transition(source=STATE_WAIT_TASK, dest=STATE_GO_TO_WAREHOUSE)
        fsm.add_transition(source=STATE_WAIT_TASK, dest=STATE_GO_TO_INSPECTION)

        fsm.add_transition(source=STATE_GO_TO_WAREHOUSE, dest=STATE_WAIT_TASK)

        fsm.add_transition(source=STATE_GO_TO_WAREHOUSE, dest=STATE_PACKAGE_DROPPED)
        fsm.add_transition(source=STATE_GO_TO_WAREHOUSE, dest=STATE_PACKAGE_DROPPED)
        fsm.add_transition(source=STATE_PACKAGE_DROPPED, dest=STATE_GO_TO_WAREHOUSE)
        fsm.add_transition(source=STATE_PACKAGE_DROPPED, dest=STATE_WAIT_TASK)

        fsm.add_transition(source=STATE_GO_TO_TERMINAL, dest=STATE_GO_TO_TERMINAL)
        fsm.add_transition(source=STATE_GO_TO_TERMINAL, dest=STATE_DELIVER_PACKAGE)
        fsm.add_transition(source=STATE_GO_TO_TERMINAL, dest=STATE_PACKAGE_DROPPED)

        fsm.add_transition(source=STATE_DELIVER_PACKAGE, dest=STATE_GO_TO_WAREHOUSE)
        fsm.add_transition(source=STATE_DELIVER_PACKAGE, dest=STATE_WAIT_TASK)

        fsm.add_transition(source=STATE_GO_TO_INSPECTION, dest=STATE_PACKAGE_INSPECTED)
        fsm.add_transition(source=STATE_PACKAGE_INSPECTED, dest=STATE_WAIT_TASK)
        
        self.add_behaviour(fsm)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-id', default='1')

    args, args_other = parser.parse_known_args()

    agent = RobotAgent(f"parvadatajs{args.id}@jix.im", "Parol3") # robots1@xmpp.jp
    agent.start()

    while True:
        time.sleep(1)