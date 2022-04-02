import multiprocessing as mp
import asyncio
import os
from MulticastPeer import MulticastPeer

async def peer_start(peer):
    await asyncio.sleep(1)

    await asyncio.gather(
        asyncio.to_thread(peer.listen),
        asyncio.to_thread(peer.test)
    )

def auto_start(peer):
    print('{0} Started'.format(os.getpid()))
    asyncio.run(peer_start(peer=peer))
    

if __name__ == '__main__':
    mp.set_start_method('spawn')
    main_queue = mp.Queue()

    peers = []

    for i in range(2):
        peers.append(MulticastPeer())
        process = mp.Process(target=auto_start, args=[peers[-1]])
        process.start()

        # main_queue.put(process)

        # print(main_queue.qsize())