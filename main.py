import multiprocessing as mp
from MulticastPeer import MulticastPeer

def AutoRun(peer:MulticastPeer):
    with mp.Pool(processes=2) as pool:
        result = pool.apply_async(peer.Listen)
        print(result.get(timeout=3))

    
if __name__ == '__main__':
    mp.set_start_method('spawn')
    main_queue = mp.Queue()

    peer_one = MulticastPeer()
    peer_two = MulticastPeer()
    peer_three = MulticastPeer()

    process_one = mp.Process(target=AutoRun, args=(peer_one))
    process_two = mp.Process(target=AutoRun, args=(peer_two))
    process_three = mp.Process(target=AutoRun, args=(peer_three))

    process_one.start()
    process_one.join()

    process_two.start()
    process_two.join()

    process_three.start()
    process_three.join()

