import multiprocessing as mp
import asyncio
from MulticastPeer import MulticastPeer

async def peer_start(peer):
    await asyncio.sleep(1)

    await asyncio.gather(
        asyncio.to_thread(peer.listen),
        asyncio.to_thread(peer.auto)
    )

def auto_start(peer):
    asyncio.run(peer_start(peer=peer))
    

if __name__ == '__main__':
    mp.set_start_method('fork')
    main_queue = mp.Queue()

    peers = []

    for i in range(3):
        peers.append(MulticastPeer())
        process = mp.Process(target=auto_start, args=[peers[-1]])
        process.start()

        # main_queue.put(process)

        # print(main_queue.qsize())