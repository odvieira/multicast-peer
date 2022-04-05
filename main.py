import multiprocessing as mp
import asyncio
import os
from MulticastPeer import MulticastPeer

def current_state(element:MulticastPeer=[]):
    print('===================================')
    print('ID: {0}\tState: {1}'.format(element.id, element.state))
    
def clear():
    os.system('clear')

if __name__ == '__main__':
    mp.set_start_method('spawn')
    main_queue = mp.Queue()

    peers = []

    for i in range(2):
        peers.append(MulticastPeer(i))
        peers[i].start()

    # while True:
    #     clear()

    #     for p in peers:
    #         current_state(p)

    #     print('===================================\n\n')

    #     action = input('Action: ')
