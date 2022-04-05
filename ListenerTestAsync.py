import asyncio
import multiprocessing as mp
from re import T
from MulticastPeer import MulticastPeer
import sys

async def main():
    mp.set_start_method('spawn')
    a, b = mp.Pipe()

    # peer = MulticastPeer(sys.argv[1])
    peer = MulticastPeer(1, pipe_end=a)
    
    q = mp.Queue()
    p = mp.Process(target=peer.listen, args=([b,True]), daemon=True)
    p.start()
    
    # task_join = asyncio.create_task(p.join())
    # task_req = asyncio.cre
    
    # R = await asyncio.gather(task_join)

    # await task_join

    print('teste, chegou')

    p.join()
    

if __name__ == '__main__':
    asyncio.run(main())
